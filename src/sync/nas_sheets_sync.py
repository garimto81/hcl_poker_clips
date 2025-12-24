"""NAS-Google Sheets 동기화 서비스

NAS 폴더의 파일 목록을 Google Sheets와 동기화합니다.
"""

import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from .nas_client import NASClient
from .sheets_client import SheetsClient, SheetsClientError
from .sync_config import SyncConfig
from .matching import FilenameNormalizer, FuzzyMatcher, MatchResult, DuplicateDetector, DuplicateGroup

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """동기화 결과"""

    matched: int = 0  # 매칭 성공 (업데이트됨)
    already_checked: int = 0  # 이미 체크되어 있음
    not_matched: int = 0  # 매칭 실패 (시트에 없음)
    errors: int = 0  # 에러 발생
    matched_files: List[str] = field(default_factory=list)  # 매칭된 파일 목록
    unmatched_files: List[str] = field(default_factory=list)  # 매칭 실패 파일 목록

    # 유사도 매칭 통계
    exact_matches: int = 0  # 정확히 일치
    normalized_matches: int = 0  # 정규화 후 일치
    fuzzy_matches: int = 0  # 유사도 매칭

    # 중복 감지 결과
    duplicate_groups: List[DuplicateGroup] = field(default_factory=list)
    duplicates_marked: int = 0  # 중복으로 표시된 파일 수

    def __str__(self) -> str:
        """결과 요약 문자열"""
        match_detail = ""
        if self.exact_matches or self.normalized_matches or self.fuzzy_matches:
            match_detail = (
                f"\n    - 정확 일치: {self.exact_matches}건"
                f"\n    - 정규화 일치: {self.normalized_matches}건"
                f"\n    - 유사도 매칭: {self.fuzzy_matches}건"
            )

        duplicate_detail = ""
        if self.duplicate_groups:
            duplicate_detail = (
                f"\n  - 중복 그룹: {len(self.duplicate_groups)}개"
                f"\n  - 중복 표시: {self.duplicates_marked}건"
            )

        return (
            f"동기화 결과:\n"
            f"  - 매칭 성공 (업데이트): {self.matched}건{match_detail}\n"
            f"  - 이미 체크됨: {self.already_checked}건\n"
            f"  - 매칭 실패: {self.not_matched}건"
            f"{duplicate_detail}\n"
            f"  - 에러: {self.errors}건"
        )


class ProgressMonitor:
    """진행 상황 모니터링"""

    def __init__(self, total: int, description: str = "처리 중"):
        """ProgressMonitor 초기화

        Args:
            total: 전체 작업 수
            description: 작업 설명
        """
        self.total = total
        self.current = 0
        self.description = description
        self.start_time = time.time()

    def update(self, current: int, message: str = ""):
        """진행률 업데이트 및 출력

        Args:
            current: 현재 진행 수
            message: 추가 메시지
        """
        self.current = current
        percent = (current / self.total) * 100 if self.total > 0 else 0
        elapsed = time.time() - self.start_time

        # 진행률 바
        bar_length = 40
        filled = int(bar_length * current / self.total) if self.total > 0 else 0
        bar = "=" * filled + "-" * (bar_length - filled)

        # 남은 시간 추정
        if current > 0:
            eta = (elapsed / current) * (self.total - current)
            eta_str = f" (예상 {eta:.0f}초)"
        else:
            eta_str = ""

        sys.stdout.write(f"\r[{bar}] {percent:.1f}% ({current}/{self.total}){eta_str} {message}")
        sys.stdout.flush()

    def finish(self, message: str = "완료"):
        """완료 메시지 출력

        Args:
            message: 완료 메시지
        """
        elapsed = time.time() - self.start_time
        print(f"\n{message} (소요 시간: {elapsed:.1f}초)")


class NASSheetsSync:
    """NAS-Google Sheets 동기화 서비스

    NAS 폴더의 파일을 Google Sheets의 Title 열과 매칭하여
    체크박스와 날짜를 업데이트합니다.
    """

    def __init__(self, config: Optional[SyncConfig] = None):
        """NASSheetsSync 초기화

        Args:
            config: 동기화 설정 (없으면 기본값 사용)
        """
        self.config = config or SyncConfig()
        self.nas: Optional[NASClient] = None
        self.sheets: Optional[SheetsClient] = None

    def _init_clients(self):
        """클라이언트 초기화"""
        if self.nas is None:
            self.nas = NASClient(self.config.nas_folder)
        if self.sheets is None:
            self.sheets = SheetsClient(self.config)

    def sync(self, dry_run: bool = False, verbose: bool = False) -> SyncResult:
        """동기화 실행

        Args:
            dry_run: True면 실제 업데이트 없이 시뮬레이션
            verbose: True면 상세 로그 출력

        Returns:
            SyncResult: 동기화 결과
        """
        result = SyncResult()
        today = date.today().strftime(self.config.date_format)

        print("=" * 60)
        print("NAS-Google Sheets 동기화 시작")
        print("=" * 60)
        print(f"NAS 폴더: {self.config.nas_folder}")
        print(f"시트: {self.config.sheet_name} (B열 Title 매칭)")
        print(f"오늘 날짜: {today}")
        if dry_run:
            print("[DRY-RUN 모드] 실제 업데이트 없음")
        print("=" * 60)
        print()

        # 1. 클라이언트 초기화
        try:
            self._init_clients()
        except Exception as e:
            logger.error(f"클라이언트 초기화 실패: {e}")
            print(f"\n[ERROR] 클라이언트 초기화 실패: {e}")
            result.errors = 1
            return result

        # 2. NAS 파일 목록 수집
        print("[1/3] NAS 파일 목록 수집 중...")
        try:
            if not self.nas.is_accessible():
                raise OSError(f"NAS 폴더에 접근할 수 없습니다: {self.config.nas_folder}")

            # 파일명과 수정 날짜를 함께 가져옴
            nas_files = self.nas.get_files_with_dates()
            print(f"  -> {len(nas_files)}개 파일 발견")
        except Exception as e:
            logger.error(f"NAS 파일 수집 실패: {e}")
            print(f"\n[ERROR] NAS 파일 수집 실패: {e}")
            result.errors = 1
            return result

        # 3. Google Sheets 데이터 로드
        print("\n[2/3] Google Sheets 데이터 로드 중...")
        try:
            sheet_data = self.sheets.get_title_column()
            print(f"  -> {len(sheet_data)}개 행 로드 완료")
        except SheetsClientError as e:
            logger.error(f"시트 데이터 로드 실패: {e}")
            print(f"\n[ERROR] 시트 데이터 로드 실패: {e}")
            result.errors = 1
            return result

        # 4. 중복 감지 (선택적)
        duplicates_to_mark: Set[str] = set()
        if self.config.duplicate_detection:
            print("\n[3/5] 중복 파일 감지 중...")
            detector = DuplicateDetector(threshold=self.config.duplicate_threshold)
            result.duplicate_groups = detector.find_duplicates(nas_files)

            if result.duplicate_groups:
                duplicates_to_mark = detector.get_duplicates_to_mark(nas_files)
                print(f"  -> {len(result.duplicate_groups)}개 중복 그룹 발견")
                print(f"  -> {len(duplicates_to_mark)}개 파일 중복으로 표시 예정")

                if verbose:
                    print(detector.generate_report(result.duplicate_groups))
            else:
                print("  -> 중복 파일 없음")

        # 5. 매칭 및 업데이트
        step_num = "4/5" if self.config.duplicate_detection else "3/3"
        print(f"\n[{step_num}] 매칭 중...")

        # 시트 Title을 정규화하여 매핑 생성
        sheet_title_to_row: Dict[str, int] = {}
        original_titles: Dict[str, str] = {}  # {정규화: 원본}

        for row_num, title in sheet_data:
            normalized = FilenameNormalizer.normalize_basic(title)
            sheet_title_to_row[normalized] = row_num
            original_titles[normalized] = title

        # 유사도 매처 초기화 (설정에 따라)
        matcher = None
        if self.config.fuzzy_enabled:
            matcher = FuzzyMatcher(
                threshold=self.config.similarity_threshold,
                method=self.config.fuzzy_method
            )

        # 매칭 수행
        updates_to_apply = []
        fuzzy_match_details = []  # 유사도 매칭 상세 정보
        filename_to_row: Dict[str, int] = {}  # 파일명 -> 행 번호 매핑 (중복 표시용)

        progress = ProgressMonitor(len(nas_files), "매칭 중")

        for i, (normalized_filename, (original_filename, file_mtime, subfolder, full_path)) in enumerate(nas_files.items()):
            progress.update(i + 1)

            match_result: Optional[MatchResult] = None

            # 기본 정규화로 정확히 일치 시도
            if normalized_filename in sheet_title_to_row:
                row_num = sheet_title_to_row[normalized_filename]
                match_result = MatchResult(
                    matched=True,
                    score=1.0,
                    match_type="exact",
                    original_filename=original_filename,
                    matched_title=original_titles.get(normalized_filename, ""),
                    matched_row=row_num,
                )
            elif matcher:
                # 유사도 매칭 시도
                match_result = matcher.find_best_match(
                    original_filename,
                    sheet_title_to_row,
                    original_titles
                )

            if match_result and match_result.matched:
                file_date = file_mtime.strftime(self.config.date_format)
                updates_to_apply.append({
                    "row": match_result.matched_row,
                    "checkbox": True,
                    "date": file_date,
                    "filename": original_filename,
                    "subfolder": subfolder,
                    "full_path": full_path,
                    "match_type": match_result.match_type,
                    "match_score": match_result.score,
                })
                result.matched_files.append(original_filename)
                filename_to_row[original_filename] = match_result.matched_row

                # 매칭 유형별 카운트
                if match_result.match_type == "exact":
                    result.exact_matches += 1
                elif match_result.match_type in ("normalized", "normalized_aggressive"):
                    result.normalized_matches += 1
                elif match_result.match_type == "fuzzy":
                    result.fuzzy_matches += 1
                    fuzzy_match_details.append(match_result)
            else:
                result.not_matched += 1
                result.unmatched_files.append(original_filename)
                if verbose:
                    logger.debug(f"매칭 실패: {original_filename}")

        progress.finish("매칭 완료")

        # 유사도 매칭 상세 출력
        if verbose and fuzzy_match_details:
            print(f"\n유사도 매칭 상세 ({len(fuzzy_match_details)}건):")
            for fm in fuzzy_match_details[:10]:
                print(f"  '{fm.original_filename[:40]}...' -> '{fm.matched_title[:40]}...' ({fm.score:.1%})")

        # 5. 업데이트 적용
        if updates_to_apply:
            print(f"\n{len(updates_to_apply)}개 행 업데이트 준비...")

            if dry_run:
                result.matched = len(updates_to_apply)
                print(f"[DRY-RUN] {len(updates_to_apply)}개 행 업데이트 예정 (실제 업데이트 없음)")
            else:
                try:
                    # 배치 업데이트 (50개씩 나누어 처리)
                    batch_size = 50
                    total_batches = (len(updates_to_apply) + batch_size - 1) // batch_size

                    for batch_num in range(total_batches):
                        start_idx = batch_num * batch_size
                        end_idx = min(start_idx + batch_size, len(updates_to_apply))
                        batch = updates_to_apply[start_idx:end_idx]

                        # 업데이트 데이터 준비 (filename 제거, subfolder와 full_path 포함)
                        batch_data = [
                            {
                                "row": u["row"],
                                "checkbox": u["checkbox"],
                                "date": u["date"],
                                "subfolder": u["subfolder"],
                                "full_path": u["full_path"],
                            }
                            for u in batch
                        ]

                        self.sheets.batch_update(batch_data)
                        result.matched += len(batch)
                        print(f"  배치 {batch_num + 1}/{total_batches} 완료 ({len(batch)}개)")

                except SheetsClientError as e:
                    logger.error(f"업데이트 실패: {e}")
                    print(f"\n[ERROR] 업데이트 실패: {e}")
                    result.errors += 1

        # 6. 중복 표시 업데이트 (T열)
        if duplicates_to_mark and not dry_run:
            step_num = "5/5" if self.config.duplicate_detection else ""
            if step_num:
                print(f"\n[{step_num}] 중복 파일 표시 중...")

            # 중복 파일명 -> 행 번호 매핑
            duplicate_rows = []
            for dup_filename in duplicates_to_mark:
                if dup_filename in filename_to_row:
                    duplicate_rows.append(filename_to_row[dup_filename])

            if duplicate_rows:
                try:
                    # 배치 업데이트 (50개씩)
                    batch_size = 50
                    for i in range(0, len(duplicate_rows), batch_size):
                        batch = duplicate_rows[i:i + batch_size]
                        self.sheets.batch_update_duplicate_column(batch, value=True)

                    result.duplicates_marked = len(duplicate_rows)
                    print(f"  -> {len(duplicate_rows)}개 파일 중복으로 표시 완료")
                except SheetsClientError as e:
                    logger.error(f"중복 표시 업데이트 실패: {e}")
                    print(f"\n[ERROR] 중복 표시 업데이트 실패: {e}")
                    result.errors += 1
        elif duplicates_to_mark and dry_run:
            # 중복 파일명 -> 행 번호 매핑
            duplicate_rows = [filename_to_row[f] for f in duplicates_to_mark if f in filename_to_row]
            result.duplicates_marked = len(duplicate_rows)
            print(f"[DRY-RUN] {len(duplicate_rows)}개 파일 중복 표시 예정 (실제 업데이트 없음)")

        # 7. 결과 출력
        print()
        print("=" * 60)
        print("동기화 완료!")
        print("=" * 60)
        print(f"  - 매칭 성공 (업데이트): {result.matched}건")
        if result.exact_matches or result.normalized_matches or result.fuzzy_matches:
            print(f"    - 정확 일치: {result.exact_matches}건")
            print(f"    - 정규화 일치: {result.normalized_matches}건")
            print(f"    - 유사도 매칭: {result.fuzzy_matches}건")
        print(f"  - 매칭 실패 (시트에 없음): {result.not_matched}건")
        if result.duplicate_groups:
            print(f"  - 중복 그룹: {len(result.duplicate_groups)}개")
            print(f"  - 중복 표시: {result.duplicates_marked}건")
        print(f"  - 에러: {result.errors}건")
        print("=" * 60)

        # 매칭 실패 파일 목록 출력 (verbose 모드)
        if verbose and result.unmatched_files:
            print("\n매칭 실패 파일 목록:")
            for filename in result.unmatched_files[:20]:  # 최대 20개만 출력
                print(f"  - {filename}")
            if len(result.unmatched_files) > 20:
                print(f"  ... 외 {len(result.unmatched_files) - 20}개")

        return result

    def get_status(self) -> Dict:
        """현재 상태 정보 반환

        Returns:
            Dict: 상태 정보
        """
        self._init_clients()

        return {
            "nas_accessible": self.nas.is_accessible(),
            "nas_file_count": self.nas.get_file_count() if self.nas.is_accessible() else 0,
            "sheet_row_count": self.sheets.get_row_count(),
            "config": str(self.config),
        }
