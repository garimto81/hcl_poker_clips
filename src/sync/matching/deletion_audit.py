"""삭제 감사 로그 모듈

모든 파일 삭제 작업을 기록하고 관리합니다.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class AuditEntry:
    """단일 감사 로그 항목"""

    timestamp: str  # ISO format
    action: str  # "DELETE", "SKIP", "ERROR"
    filename: str
    full_path: str
    size: int  # bytes
    mtime: str  # ISO format
    reason: str  # 예: "duplicate of 'Amazing Hand.mp4'"
    similarity_score: float
    size_variance: float  # 0.0 ~ 1.0 (예: 0.05 = 5%)
    kept_file: str  # 유지된 파일명
    dry_run: bool = False


@dataclass
class AuditLog:
    """감사 로그 메타데이터"""

    version: str = "1.0"
    created: str = ""
    last_updated: str = ""
    total_entries: int = 0
    entries: List[AuditEntry] = field(default_factory=list)


class DeletionAuditLog:
    """삭제 감사 로그 관리 클래스

    모든 파일 삭제 작업을 JSON 형식으로 기록합니다.
    """

    def __init__(
        self,
        log_path: str = "logs/deletion_audit.json",
        max_entries: int = 10000,
    ):
        """DeletionAuditLog 초기화

        Args:
            log_path: 감사 로그 파일 경로
            max_entries: 최대 로그 항목 수 (초과 시 오래된 항목 삭제)
        """
        self.log_path = Path(log_path)
        self.max_entries = max_entries
        self._audit_log: Optional[AuditLog] = None

    def _ensure_directory(self):
        """로그 디렉토리 생성"""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_log(self) -> AuditLog:
        """기존 로그 파일 로드 또는 새로 생성"""
        if self._audit_log is not None:
            return self._audit_log

        if self.log_path.exists():
            try:
                with open(self.log_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                entries = [AuditEntry(**e) for e in data.get("entries", [])]
                self._audit_log = AuditLog(
                    version=data.get("version", "1.0"),
                    created=data.get("created", ""),
                    last_updated=data.get("last_updated", ""),
                    total_entries=len(entries),
                    entries=entries,
                )
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"감사 로그 파일 로드 실패, 새로 생성: {e}")
                self._audit_log = AuditLog(
                    created=datetime.now().isoformat(),
                    last_updated=datetime.now().isoformat(),
                )
        else:
            self._audit_log = AuditLog(
                created=datetime.now().isoformat(),
                last_updated=datetime.now().isoformat(),
            )

        return self._audit_log

    def _save_log(self):
        """로그 파일 저장"""
        self._ensure_directory()

        log = self._load_log()
        log.last_updated = datetime.now().isoformat()
        log.total_entries = len(log.entries)

        data = {
            "version": log.version,
            "created": log.created,
            "last_updated": log.last_updated,
            "total_entries": log.total_entries,
            "entries": [asdict(e) for e in log.entries],
        }

        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _rotate_if_needed(self):
        """최대 항목 수 초과 시 오래된 항목 삭제"""
        log = self._load_log()

        if len(log.entries) > self.max_entries:
            # 오래된 항목부터 삭제 (가장 오래된 것 제거)
            excess = len(log.entries) - self.max_entries
            log.entries = log.entries[excess:]
            logger.info(f"감사 로그 로테이션: {excess}개 오래된 항목 삭제")

    def log_deletion(
        self,
        filename: str,
        full_path: str,
        size: int,
        mtime: datetime,
        similarity_score: float,
        size_variance: float,
        kept_file: str,
        dry_run: bool = False,
    ):
        """삭제 작업 기록

        Args:
            filename: 삭제된 파일명
            full_path: 전체 경로
            size: 파일 크기 (bytes)
            mtime: 수정 시간
            similarity_score: 유사도 점수
            size_variance: 크기 차이 비율
            kept_file: 유지된 파일명
            dry_run: dry-run 모드 여부
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action="DELETE",
            filename=filename,
            full_path=full_path,
            size=size,
            mtime=mtime.isoformat() if isinstance(mtime, datetime) else str(mtime),
            reason=f"duplicate of '{kept_file}'",
            similarity_score=similarity_score,
            size_variance=size_variance,
            kept_file=kept_file,
            dry_run=dry_run,
        )

        log = self._load_log()
        log.entries.append(entry)

        self._rotate_if_needed()
        self._save_log()

        logger.debug(f"삭제 로그 기록: {filename} (dry_run={dry_run})")

    def log_skip(
        self,
        filename: str,
        full_path: str,
        size: int,
        mtime: datetime,
        reason: str,
    ):
        """건너뛴 파일 기록

        Args:
            filename: 파일명
            full_path: 전체 경로
            size: 파일 크기
            mtime: 수정 시간
            reason: 건너뛴 이유
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action="SKIP",
            filename=filename,
            full_path=full_path,
            size=size,
            mtime=mtime.isoformat() if isinstance(mtime, datetime) else str(mtime),
            reason=reason,
            similarity_score=0.0,
            size_variance=0.0,
            kept_file="",
            dry_run=False,
        )

        log = self._load_log()
        log.entries.append(entry)

        self._rotate_if_needed()
        self._save_log()

        logger.debug(f"건너뛰기 로그 기록: {filename} - {reason}")

    def log_error(
        self,
        filename: str,
        full_path: str,
        error_message: str,
    ):
        """에러 기록

        Args:
            filename: 파일명
            full_path: 전체 경로
            error_message: 에러 메시지
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action="ERROR",
            filename=filename,
            full_path=full_path,
            size=0,
            mtime="",
            reason=error_message,
            similarity_score=0.0,
            size_variance=0.0,
            kept_file="",
            dry_run=False,
        )

        log = self._load_log()
        log.entries.append(entry)

        self._rotate_if_needed()
        self._save_log()

        logger.error(f"에러 로그 기록: {filename} - {error_message}")

    def get_recent_entries(self, limit: int = 100) -> List[AuditEntry]:
        """최근 감사 로그 항목 조회

        Args:
            limit: 반환할 최대 항목 수

        Returns:
            List[AuditEntry]: 최근 항목 목록 (최신순)
        """
        log = self._load_log()
        return log.entries[-limit:][::-1]  # 최신순 정렬

    def get_statistics(self) -> dict:
        """감사 로그 통계

        Returns:
            통계 딕셔너리
        """
        log = self._load_log()

        delete_count = sum(1 for e in log.entries if e.action == "DELETE" and not e.dry_run)
        skip_count = sum(1 for e in log.entries if e.action == "SKIP")
        error_count = sum(1 for e in log.entries if e.action == "ERROR")
        dry_run_count = sum(1 for e in log.entries if e.action == "DELETE" and e.dry_run)

        total_bytes_deleted = sum(
            e.size for e in log.entries if e.action == "DELETE" and not e.dry_run
        )

        return {
            "total_entries": log.total_entries,
            "files_deleted": delete_count,
            "files_skipped": skip_count,
            "errors": error_count,
            "dry_run_deletions": dry_run_count,
            "total_bytes_freed": total_bytes_deleted,
            "total_gb_freed": round(total_bytes_deleted / (1024 ** 3), 2),
            "log_created": log.created,
            "last_updated": log.last_updated,
        }

    def export_csv(self, output_path: str):
        """감사 로그를 CSV로 내보내기

        Args:
            output_path: 출력 파일 경로
        """
        import csv

        log = self._load_log()

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "timestamp", "action", "filename", "full_path", "size",
                "mtime", "reason", "similarity_score", "size_variance",
                "kept_file", "dry_run"
            ])
            writer.writeheader()
            for entry in log.entries:
                writer.writerow(asdict(entry))

        logger.info(f"감사 로그 CSV 내보내기 완료: {output_path}")

    def clear(self):
        """감사 로그 초기화 (주의!)"""
        self._audit_log = AuditLog(
            created=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
        )
        self._save_log()
        logger.warning("감사 로그가 초기화되었습니다.")
