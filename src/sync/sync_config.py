"""동기화 설정 모듈

환경변수와 config.ini에서 설정을 로드합니다.
"""

import os
import configparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class SyncConfig:
    """NAS-Google Sheets 동기화 설정

    우선순위: 환경변수 > config.ini > 기본값
    """

    # NAS 설정
    nas_folder: str = field(default="X:\\GGP Footage\\HCL Clips")

    # Google Sheets 설정
    credentials_path: str = field(default="D:\\AI\\claude01\\json\\service_account_key.json")
    spreadsheet_id: str = field(default="1h27Ha7pR-iYK_Gik8F4FfSvsk4s89sxk49CsU3XP_m4")
    sheet_name: str = field(default="HCL_Clips")

    # 열 매핑
    title_column: str = field(default="B")
    checkbox_column: str = field(default="P")
    date_column: str = field(default="Q")
    subfolder_column: str = field(default="R")
    path_column: str = field(default="S")

    # 처리 설정
    data_start_row: int = field(default=2)
    date_format: str = field(default="%Y-%m-%d")

    # API 설정
    api_delay: float = field(default=1.2)
    max_retries: int = field(default=5)

    # 유사도 매칭 설정
    fuzzy_enabled: bool = field(default=True)
    similarity_threshold: float = field(default=0.85)
    fuzzy_method: str = field(default="token_sort_ratio")

    # 중복 감지 설정
    duplicate_detection: bool = field(default=True)
    duplicate_threshold: float = field(default=0.95)
    duplicate_column: str = field(default="T")

    # 중복 파일 정리 설정
    cleanup_enabled: bool = field(default=False)  # 기본 비활성화 (안전)
    cleanup_similarity_threshold: float = field(default=0.85)  # 파일명 유사도 85%
    cleanup_size_variance: float = field(default=0.10)  # 크기 차이 10%
    cleanup_audit_log: str = field(default="logs/deletion_audit.json")
    cleanup_require_confirmation: bool = field(default=True)  # 확인 필요

    def __post_init__(self):
        """환경변수와 config.ini에서 설정 로드"""
        self._load_from_config_ini()
        self._load_from_env()

    def _load_from_config_ini(self):
        """config.ini [SHEETS_SYNC] 섹션에서 설정 로드"""
        config_path = Path(__file__).parent.parent.parent / "config.ini"

        if not config_path.exists():
            return

        config = configparser.ConfigParser()
        config.read(config_path, encoding="utf-8")

        if "SHEETS_SYNC" not in config:
            return

        section = config["SHEETS_SYNC"]

        # NAS 설정
        if "NAS_FOLDER" in section:
            self.nas_folder = section["NAS_FOLDER"]

        # Google Sheets 설정
        if "CREDENTIALS_PATH" in section:
            self.credentials_path = section["CREDENTIALS_PATH"]
        if "SPREADSHEET_ID" in section:
            self.spreadsheet_id = section["SPREADSHEET_ID"]
        if "SHEET_NAME" in section:
            self.sheet_name = section["SHEET_NAME"]

        # 열 매핑
        if "TITLE_COLUMN" in section:
            self.title_column = section["TITLE_COLUMN"]
        if "CHECKBOX_COLUMN" in section:
            self.checkbox_column = section["CHECKBOX_COLUMN"]
        if "DATE_COLUMN" in section:
            self.date_column = section["DATE_COLUMN"]
        if "SUBFOLDER_COLUMN" in section:
            self.subfolder_column = section["SUBFOLDER_COLUMN"]
        if "PATH_COLUMN" in section:
            self.path_column = section["PATH_COLUMN"]

        # 처리 설정
        if "DATA_START_ROW" in section:
            self.data_start_row = int(section["DATA_START_ROW"])
        if "DATE_FORMAT" in section:
            # configparser의 % escaping 처리 (%% -> %)
            self.date_format = section["DATE_FORMAT"].replace("%%", "%")

        # API 설정
        if "API_DELAY" in section:
            self.api_delay = float(section["API_DELAY"])
        if "MAX_RETRIES" in section:
            self.max_retries = int(section["MAX_RETRIES"])

        # 유사도 매칭 설정
        if "FUZZY_ENABLED" in section:
            self.fuzzy_enabled = section["FUZZY_ENABLED"].lower() in ("true", "1", "yes")
        if "SIMILARITY_THRESHOLD" in section:
            self.similarity_threshold = float(section["SIMILARITY_THRESHOLD"])
        if "FUZZY_METHOD" in section:
            self.fuzzy_method = section["FUZZY_METHOD"]

        # 중복 감지 설정
        if "DUPLICATE_DETECTION" in section:
            self.duplicate_detection = section["DUPLICATE_DETECTION"].lower() in ("true", "1", "yes")
        if "DUPLICATE_THRESHOLD" in section:
            self.duplicate_threshold = float(section["DUPLICATE_THRESHOLD"])
        if "DUPLICATE_COLUMN" in section:
            self.duplicate_column = section["DUPLICATE_COLUMN"]

        # 중복 파일 정리 설정 ([DUPLICATE_CLEANUP] 섹션)
        if "DUPLICATE_CLEANUP" in config:
            cleanup = config["DUPLICATE_CLEANUP"]
            if "CLEANUP_ENABLED" in cleanup:
                self.cleanup_enabled = cleanup["CLEANUP_ENABLED"].lower() in ("true", "1", "yes")
            if "CLEANUP_SIMILARITY_THRESHOLD" in cleanup:
                self.cleanup_similarity_threshold = float(cleanup["CLEANUP_SIMILARITY_THRESHOLD"])
            if "CLEANUP_SIZE_VARIANCE" in cleanup:
                self.cleanup_size_variance = float(cleanup["CLEANUP_SIZE_VARIANCE"])
            if "CLEANUP_AUDIT_LOG" in cleanup:
                self.cleanup_audit_log = cleanup["CLEANUP_AUDIT_LOG"]
            if "CLEANUP_REQUIRE_CONFIRMATION" in cleanup:
                self.cleanup_require_confirmation = cleanup["CLEANUP_REQUIRE_CONFIRMATION"].lower() in ("true", "1", "yes")

    def _load_from_env(self):
        """환경변수에서 설정 로드 (최우선)"""
        # NAS 설정
        if os.environ.get("NAS_FOLDER"):
            self.nas_folder = os.environ["NAS_FOLDER"]

        # Google Sheets 설정
        if os.environ.get("GOOGLE_CREDENTIALS_PATH"):
            self.credentials_path = os.environ["GOOGLE_CREDENTIALS_PATH"]
        if os.environ.get("SPREADSHEET_ID"):
            self.spreadsheet_id = os.environ["SPREADSHEET_ID"]
        if os.environ.get("SHEET_NAME"):
            self.sheet_name = os.environ["SHEET_NAME"]

        # 열 매핑
        if os.environ.get("TITLE_COLUMN"):
            self.title_column = os.environ["TITLE_COLUMN"]
        if os.environ.get("CHECKBOX_COLUMN"):
            self.checkbox_column = os.environ["CHECKBOX_COLUMN"]
        if os.environ.get("DATE_COLUMN"):
            self.date_column = os.environ["DATE_COLUMN"]

    def validate(self) -> bool:
        """설정 유효성 검사

        Returns:
            bool: 설정이 유효하면 True

        Raises:
            ValueError: 필수 설정이 누락되었거나 잘못된 경우
        """
        errors = []

        # NAS 폴더 경로 확인
        if not self.nas_folder:
            errors.append("NAS_FOLDER가 설정되지 않았습니다.")

        # 인증 파일 경로 확인
        if not self.credentials_path:
            errors.append("CREDENTIALS_PATH가 설정되지 않았습니다.")
        elif not Path(self.credentials_path).exists():
            errors.append(f"인증 파일이 존재하지 않습니다: {self.credentials_path}")

        # Spreadsheet ID 확인
        if not self.spreadsheet_id:
            errors.append("SPREADSHEET_ID가 설정되지 않았습니다.")

        # 시트 이름 확인
        if not self.sheet_name:
            errors.append("SHEET_NAME이 설정되지 않았습니다.")

        if errors:
            raise ValueError("\n".join(errors))

        return True

    def __str__(self) -> str:
        """설정 요약 문자열 반환"""
        return (
            f"SyncConfig:\n"
            f"  NAS 폴더: {self.nas_folder}\n"
            f"  스프레드시트 ID: {self.spreadsheet_id}\n"
            f"  시트 이름: {self.sheet_name}\n"
            f"  매칭 열: {self.title_column} (Title)\n"
            f"  체크박스 열: {self.checkbox_column}\n"
            f"  날짜 열: {self.date_column}\n"
            f"  서브폴더 열: {self.subfolder_column}\n"
            f"  경로 열: {self.path_column}\n"
            f"  중복 열: {self.duplicate_column}\n"
            f"  데이터 시작 행: {self.data_start_row}\n"
            f"  유사도 매칭: {'활성화' if self.fuzzy_enabled else '비활성화'} (임계값: {self.similarity_threshold})\n"
            f"  중복 감지: {'활성화' if self.duplicate_detection else '비활성화'} (임계값: {self.duplicate_threshold})\n"
            f"  중복 정리: {'활성화' if self.cleanup_enabled else '비활성화'} "
            f"(유사도: {self.cleanup_similarity_threshold}, 크기차이: {self.cleanup_size_variance:.0%})"
        )
