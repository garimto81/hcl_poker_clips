"""중복 파일 정리 모듈

파일명 유사도 + 크기 검증을 통해 중복 파일을 감지하고 삭제합니다.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple

from .deletion_audit import DeletionAuditLog
from .duplicate_detector import DuplicateDetector, DuplicateGroup

logger = logging.getLogger(__name__)


@dataclass
class DeletionCandidate:
    """삭제 대상 파일"""

    filename: str  # 원본 파일명 (확장자 제외)
    full_path: str  # 전체 경로
    size: int  # 파일 크기 (bytes)
    mtime: datetime  # 수정 시간
    reason: str  # 삭제 이유 (예: "duplicate of 'Amazing Hand'")
    similarity_score: float  # 유사도 점수
    size_variance: float  # 크기 차이 비율 (0.0 ~ 1.0)
    kept_file: str  # 유지될 파일명


@dataclass
class CleanupResult:
    """정리 작업 결과"""

    total_groups: int = 0  # 중복 그룹 수
    files_analyzed: int = 0  # 분석된 파일 수
    files_deleted: int = 0  # 삭제된 파일 수
    files_skipped: int = 0  # 건너뛴 파일 수 (크기 검증 실패)
    bytes_freed: int = 0  # 해제된 바이트
    deleted_files: List[DeletionCandidate] = field(default_factory=list)
    skipped_files: List[Tuple[str, str]] = field(default_factory=list)  # [(filename, reason)]
    errors: List[Tuple[str, str]] = field(default_factory=list)  # [(filename, error)]
    dry_run: bool = True

    @property
    def gb_freed(self) -> float:
        """해제된 용량 (GB)"""
        return round(self.bytes_freed / (1024 ** 3), 2)


class DuplicateCleaner:
    """중복 파일 정리 클래스

    파일명 유사도와 크기 검증을 조합하여 중복 파일을 삭제합니다.

    Detection Criteria:
    1. 파일명 유사도 >= similarity_threshold (기본: 85%)
    2. 파일 크기 차이 <= size_variance_threshold (기본: 10%)

    Keep Rule: 최신 파일 유지 (mtime 기준)
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        size_variance_threshold: float = 0.10,
        audit_log_path: str = "logs/deletion_audit.json",
    ):
        """DuplicateCleaner 초기화

        Args:
            similarity_threshold: 파일명 유사도 임계값 (0.0-1.0, 기본: 0.85)
            size_variance_threshold: 크기 차이 허용 비율 (0.0-1.0, 기본: 0.10 = 10%)
            audit_log_path: 감사 로그 파일 경로
        """
        self.similarity_threshold = similarity_threshold
        self.size_variance_threshold = size_variance_threshold
        self.detector = DuplicateDetector(threshold=similarity_threshold)
        self.audit = DeletionAuditLog(log_path=audit_log_path)

    def check_size_variance(
        self,
        size1: int,
        size2: int,
    ) -> Tuple[bool, float]:
        """두 파일의 크기 차이가 임계값 이내인지 확인

        Args:
            size1: 첫 번째 파일 크기 (bytes)
            size2: 두 번째 파일 크기 (bytes)

        Returns:
            Tuple[bool, float]: (임계값 이내 여부, 차이 비율)
        """
        if size1 == 0 or size2 == 0:
            # 크기 정보가 없으면 검증 불가 → 삭제 제외
            return False, 1.0

        # 큰 크기를 기준으로 차이 계산
        max_size = max(size1, size2)
        min_size = min(size1, size2)
        variance = (max_size - min_size) / max_size

        is_within = variance <= self.size_variance_threshold

        return is_within, variance

    def find_cleanup_candidates(
        self,
        files: Dict[str, Tuple[str, datetime, str, str]],  # NASClient.get_files_with_dates() 형식
        file_sizes: Dict[str, int],  # {원본_파일명: 크기}
    ) -> Tuple[List[DeletionCandidate], List[DuplicateGroup]]:
        """삭제 대상 파일 찾기

        파일명 유사도 검사 후 크기 검증을 추가로 수행합니다.

        Args:
            files: NASClient.get_files_with_dates()의 반환값
            file_sizes: 파일 크기 매핑 {원본_파일명: 크기(bytes)}

        Returns:
            Tuple[List[DeletionCandidate], List[DuplicateGroup]]: (삭제 후보, 중복 그룹)
        """
        # 1. 파일명 유사도 기반 중복 그룹 찾기
        groups = self.detector.find_duplicates(files, file_sizes)

        candidates: List[DeletionCandidate] = []

        for group in groups:
            # 2. 그룹 내 파일들의 크기 검증
            # recommended 파일의 크기 가져오기
            recommended_size = 0
            recommended_name = group.recommended

            for name, path, mtime, size in group.files:
                if name == recommended_name:
                    recommended_size = size
                    break

            # 각 중복 파일 검증
            for name, path, mtime, size in group.files:
                if name == recommended_name:
                    # 유지할 파일은 건너뛰기
                    continue

                # 크기 검증
                is_valid, variance = self.check_size_variance(recommended_size, size)

                if not is_valid:
                    # 크기 차이가 크면 삭제 제외
                    logger.debug(
                        f"크기 검증 실패 (제외): {name} "
                        f"(차이: {variance:.1%}, 임계값: {self.size_variance_threshold:.1%})"
                    )
                    continue

                # 유사도 점수 찾기
                similarity = 1.0
                for (fname, _, _, _), score in zip(group.files, group.similarity_scores):
                    if fname == name:
                        similarity = score
                        break

                candidate = DeletionCandidate(
                    filename=name,
                    full_path=path,
                    size=size,
                    mtime=mtime,
                    reason=f"duplicate of '{recommended_name}'",
                    similarity_score=similarity,
                    size_variance=variance,
                    kept_file=recommended_name,
                )
                candidates.append(candidate)

        return candidates, groups

    def cleanup(
        self,
        files: Dict[str, Tuple[str, datetime, str, str]],
        file_sizes: Dict[str, int],
        dry_run: bool = True,
        confirm_callback: Optional[Callable[[List[DeletionCandidate]], bool]] = None,
    ) -> CleanupResult:
        """중복 파일 정리 실행

        Args:
            files: NASClient.get_files_with_dates()의 반환값
            file_sizes: 파일 크기 매핑
            dry_run: True면 삭제 시뮬레이션만 (기본값)
            confirm_callback: 삭제 전 확인 콜백 (삭제 후보 리스트 → True/False)

        Returns:
            CleanupResult: 정리 결과
        """
        result = CleanupResult(dry_run=dry_run)

        # 1. 삭제 후보 찾기
        candidates, groups = self.find_cleanup_candidates(files, file_sizes)

        result.total_groups = len(groups)
        result.files_analyzed = len(files)

        if not candidates:
            logger.info("삭제할 중복 파일이 없습니다.")
            return result

        # 2. 확인 콜백 (있는 경우)
        if confirm_callback and not dry_run:
            if not confirm_callback(candidates):
                logger.info("사용자가 삭제를 취소했습니다.")
                return result

        # 3. 파일 삭제 (또는 시뮬레이션)
        for candidate in candidates:
            if dry_run:
                # Dry-run: 로그만 기록
                result.deleted_files.append(candidate)
                result.files_deleted += 1
                result.bytes_freed += candidate.size

                self.audit.log_deletion(
                    filename=candidate.filename,
                    full_path=candidate.full_path,
                    size=candidate.size,
                    mtime=candidate.mtime,
                    similarity_score=candidate.similarity_score,
                    size_variance=candidate.size_variance,
                    kept_file=candidate.kept_file,
                    dry_run=True,
                )

                logger.info(f"[DRY-RUN] 삭제 예정: {candidate.filename}")
            else:
                # 실제 삭제
                success = self._delete_file(candidate)

                if success:
                    result.deleted_files.append(candidate)
                    result.files_deleted += 1
                    result.bytes_freed += candidate.size

                    self.audit.log_deletion(
                        filename=candidate.filename,
                        full_path=candidate.full_path,
                        size=candidate.size,
                        mtime=candidate.mtime,
                        similarity_score=candidate.similarity_score,
                        size_variance=candidate.size_variance,
                        kept_file=candidate.kept_file,
                        dry_run=False,
                    )
                else:
                    result.errors.append((candidate.filename, "삭제 실패"))

        return result

    def _delete_file(self, candidate: DeletionCandidate) -> bool:
        """단일 파일 삭제

        Args:
            candidate: 삭제 대상 정보

        Returns:
            bool: 삭제 성공 여부
        """
        path = Path(candidate.full_path)

        try:
            if not path.exists():
                logger.warning(f"파일이 존재하지 않습니다: {candidate.full_path}")
                self.audit.log_error(
                    filename=candidate.filename,
                    full_path=candidate.full_path,
                    error_message="파일이 존재하지 않습니다",
                )
                return False

            # 파일 삭제
            os.remove(candidate.full_path)
            logger.info(f"삭제 완료: {candidate.filename} ({candidate.size / (1024**2):.1f} MB)")
            return True

        except PermissionError as e:
            logger.error(f"권한 오류: {candidate.full_path} - {e}")
            self.audit.log_error(
                filename=candidate.filename,
                full_path=candidate.full_path,
                error_message=f"권한 오류: {e}",
            )
            return False

        except OSError as e:
            logger.error(f"삭제 실패: {candidate.full_path} - {e}")
            self.audit.log_error(
                filename=candidate.filename,
                full_path=candidate.full_path,
                error_message=str(e),
            )
            return False

    def generate_preview(
        self,
        candidates: List[DeletionCandidate],
        groups: List[DuplicateGroup],
    ) -> str:
        """삭제 미리보기 생성

        Args:
            candidates: 삭제 후보 목록
            groups: 중복 그룹 목록

        Returns:
            포맷된 미리보기 문자열
        """
        lines = ["=" * 70]
        lines.append("DUPLICATE CLEANUP PREVIEW")
        lines.append("=" * 70)
        lines.append("")

        total_bytes = sum(c.size for c in candidates)
        lines.append(f"발견된 중복 그룹: {len(groups)}개")
        lines.append(f"삭제 예정 파일: {len(candidates)}개")
        lines.append(f"절약 예상 용량: {total_bytes / (1024**3):.2f} GB")
        lines.append("")

        # 그룹별 상세 정보
        for i, group in enumerate(groups, 1):
            lines.append(f"그룹 {i}: \"{group.canonical_name[:40]}...\"")
            lines.append("-" * 50)

            for name, path, mtime, size in group.files:
                date_str = mtime.strftime("%Y-%m-%d")
                size_mb = size / (1024 ** 2)

                if name == group.recommended:
                    marker = "[KEEP]  "
                else:
                    # 이 파일이 삭제 대상인지 확인
                    is_candidate = any(c.filename == name for c in candidates)
                    if is_candidate:
                        marker = "[DELETE]"
                    else:
                        marker = "[SKIP]  "

                lines.append(f"  {marker} {name[:50]}")
                lines.append(f"          ({date_str}, {size_mb:.1f} MB)")

            lines.append("")

        lines.append("=" * 70)
        lines.append(f"WARNING: {len(candidates)}개 파일이 영구 삭제됩니다!")
        lines.append("=" * 70)

        return "\n".join(lines)

    def get_audit_statistics(self) -> dict:
        """감사 로그 통계 반환"""
        return self.audit.get_statistics()
