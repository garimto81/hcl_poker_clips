"""NAS 파일 시스템 클라이언트

NAS 폴더의 파일 목록을 스캔하고 관리합니다.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """파일 정보"""

    name: str  # 전체 파일명 (확장자 포함)
    stem: str  # 확장자 제외 파일명
    suffix: str  # 확장자
    size: int  # 파일 크기 (bytes)
    mtime: datetime  # 수정 시간
    subfolder: str = ""  # 서브폴더 이름 (예: "2024")
    full_path: str = ""  # 전체 경로


class NASClient:
    """NAS 파일 시스템 클라이언트

    NAS 폴더의 파일 목록을 스캔하고 파일 정보를 제공합니다.
    """

    # 지원하는 비디오 확장자
    VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}

    def __init__(self, folder_path: str):
        """NASClient 초기화

        Args:
            folder_path: NAS 폴더 경로
        """
        self.folder_path = Path(folder_path)
        self._files_cache: Optional[List[FileInfo]] = None

    def is_accessible(self) -> bool:
        """NAS 폴더 접근 가능 여부 확인

        Returns:
            bool: 접근 가능하면 True
        """
        try:
            return self.folder_path.exists() and self.folder_path.is_dir()
        except (OSError, PermissionError) as e:
            logger.error(f"NAS 폴더 접근 실패: {e}")
            return False

    def get_files(self, video_only: bool = True, recursive: bool = True) -> List[FileInfo]:
        """폴더 내 파일 목록 반환

        Args:
            video_only: True면 비디오 파일만 반환
            recursive: True면 하위 폴더도 재귀적으로 검색

        Returns:
            List[FileInfo]: 파일 정보 목록
        """
        if not self.is_accessible():
            raise OSError(f"NAS 폴더에 접근할 수 없습니다: {self.folder_path}")

        files = []

        # 재귀적 검색 또는 현재 폴더만
        if recursive:
            paths = self.folder_path.rglob("*")
        else:
            paths = self.folder_path.iterdir()

        for path in paths:
            if not path.is_file():
                continue

            # 비디오 파일만 필터링
            if video_only and path.suffix.lower() not in self.VIDEO_EXTENSIONS:
                continue

            try:
                stat = path.stat()

                # 서브폴더 추출
                try:
                    relative = path.relative_to(self.folder_path)
                    subfolder = relative.parent.as_posix()
                    if subfolder == ".":
                        subfolder = ""
                except ValueError:
                    subfolder = ""

                files.append(
                    FileInfo(
                        name=path.name,
                        stem=path.stem,
                        suffix=path.suffix,
                        size=stat.st_size,
                        mtime=datetime.fromtimestamp(stat.st_mtime),
                        subfolder=subfolder,
                        full_path=str(path),
                    )
                )
            except (OSError, PermissionError) as e:
                logger.warning(f"파일 정보 읽기 실패: {path} - {e}")
                continue

        logger.info(f"NAS 폴더에서 {len(files)}개 파일 발견 (하위 폴더 포함: {recursive})")
        return files

    def get_file_stems(self, video_only: bool = True) -> Set[str]:
        """확장자 제외 파일명 집합 반환

        Args:
            video_only: True면 비디오 파일만 포함

        Returns:
            Set[str]: 파일명 집합 (확장자 제외)
        """
        files = self.get_files(video_only=video_only)
        return {f.stem for f in files}

    def get_file_stems_normalized(self, video_only: bool = True) -> Dict[str, str]:
        """정규화된 파일명 매핑 반환

        대소문자 무시, 특수문자 정규화된 키와 원본 파일명 매핑

        Args:
            video_only: True면 비디오 파일만 포함

        Returns:
            Dict[str, str]: {정규화된_파일명: 원본_파일명}
        """
        files = self.get_files(video_only=video_only)
        result = {}

        for f in files:
            normalized = self._normalize_filename(f.stem)
            result[normalized] = f.stem

        return result

    def get_files_with_dates(self, video_only: bool = True) -> Dict[str, Tuple[str, datetime, str, str]]:
        """정규화된 파일명과 수정 날짜, 서브폴더, 전체 경로 매핑 반환

        Args:
            video_only: True면 비디오 파일만 포함

        Returns:
            Dict[str, Tuple[str, datetime, str, str]]: {정규화된_파일명: (원본_파일명, 수정일시, 서브폴더, 전체경로)}
        """
        files = self.get_files(video_only=video_only)
        result = {}

        for f in files:
            normalized = self._normalize_filename(f.stem)
            result[normalized] = (f.stem, f.mtime, f.subfolder, f.full_path)

        return result

    @staticmethod
    def _normalize_filename(filename: str) -> str:
        """파일명 정규화

        - 소문자 변환
        - 모든 공백 제거
        - 앞뒤 공백 제거

        Args:
            filename: 원본 파일명

        Returns:
            str: 정규화된 파일명
        """
        # 소문자 변환 + 모든 공백 제거
        return filename.lower().replace(" ", "").strip()

    def get_file_count(self, video_only: bool = True) -> int:
        """파일 개수 반환

        Args:
            video_only: True면 비디오 파일만 카운트

        Returns:
            int: 파일 개수
        """
        return len(self.get_files(video_only=video_only))

    def get_file_sizes(self, video_only: bool = True) -> Dict[str, int]:
        """파일 크기 매핑 반환

        Args:
            video_only: True면 비디오 파일만 포함

        Returns:
            Dict[str, int]: {파일명(확장자 제외): 크기(bytes)}
        """
        files = self.get_files(video_only=video_only)
        return {f.stem: f.size for f in files}

    def get_full_file_info(self, video_only: bool = True) -> Dict[str, FileInfo]:
        """전체 파일 정보 매핑 반환

        Args:
            video_only: True면 비디오 파일만 포함

        Returns:
            Dict[str, FileInfo]: {정규화된_파일명: FileInfo}
        """
        files = self.get_files(video_only=video_only)
        return {self._normalize_filename(f.stem): f for f in files}

    def delete_file(self, file_path: str) -> bool:
        """파일 삭제

        Args:
            file_path: 삭제할 파일의 전체 경로

        Returns:
            bool: 삭제 성공 여부

        Raises:
            PermissionError: 권한 부족
            OSError: 파일 시스템 오류
        """
        import os

        path = Path(file_path)

        if not path.exists():
            logger.warning(f"삭제할 파일이 존재하지 않습니다: {file_path}")
            return False

        if not path.is_file():
            logger.warning(f"파일이 아닙니다: {file_path}")
            return False

        try:
            os.remove(file_path)
            logger.info(f"파일 삭제 완료: {file_path}")
            return True
        except PermissionError as e:
            logger.error(f"삭제 권한 오류: {file_path} - {e}")
            raise
        except OSError as e:
            logger.error(f"파일 삭제 실패: {file_path} - {e}")
            raise

    def get_file_info_by_path(self, file_path: str) -> Optional[FileInfo]:
        """경로로 파일 정보 조회

        Args:
            file_path: 파일 전체 경로

        Returns:
            FileInfo 또는 None
        """
        path = Path(file_path)

        if not path.exists() or not path.is_file():
            return None

        try:
            stat = path.stat()

            # 서브폴더 추출
            try:
                relative = path.relative_to(self.folder_path)
                subfolder = relative.parent.as_posix()
                if subfolder == ".":
                    subfolder = ""
            except ValueError:
                subfolder = ""

            return FileInfo(
                name=path.name,
                stem=path.stem,
                suffix=path.suffix,
                size=stat.st_size,
                mtime=datetime.fromtimestamp(stat.st_mtime),
                subfolder=subfolder,
                full_path=str(path),
            )
        except (OSError, PermissionError) as e:
            logger.warning(f"파일 정보 조회 실패: {file_path} - {e}")
            return None

    def __str__(self) -> str:
        """클라이언트 정보 문자열 반환"""
        accessible = "접근 가능" if self.is_accessible() else "접근 불가"
        return f"NASClient({self.folder_path}) - {accessible}"
