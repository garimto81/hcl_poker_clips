"""Google Sheets API 클라이언트

Service Account 인증을 사용하여 Google Sheets API와 통신합니다.
Rate Limit 대응을 위한 Exponential Backoff를 구현합니다.
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .sync_config import SyncConfig

logger = logging.getLogger(__name__)


class SheetsClientError(Exception):
    """Sheets 클라이언트 기본 예외"""

    pass


class SheetsAuthError(SheetsClientError):
    """인증 실패 예외"""

    pass


class SheetsRateLimitError(SheetsClientError):
    """Rate Limit 초과 예외"""

    pass


class SheetsClient:
    """Google Sheets API 클라이언트

    Service Account 인증을 사용하며, Rate Limit 대응을 위한
    Exponential Backoff를 구현합니다.

    API 한도 (Google 공식 문서 기준):
    - 읽기: 60회/분/유저, 300회/분/프로젝트
    - 쓰기: 60회/분/유저, 300회/분/프로젝트
    """

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self, config: SyncConfig):
        """SheetsClient 초기화

        Args:
            config: 동기화 설정
        """
        self.config = config
        self.api_delay = config.api_delay
        self.max_retries = config.max_retries
        self._service = None
        self._connect()

    def _connect(self):
        """Google Sheets API 연결"""
        try:
            creds = service_account.Credentials.from_service_account_file(
                self.config.credentials_path, scopes=self.SCOPES
            )
            self._service = build("sheets", "v4", credentials=creds)
            logger.info("Google Sheets API 연결 성공")
        except FileNotFoundError:
            raise SheetsAuthError(
                f"Service Account 키 파일을 찾을 수 없습니다: {self.config.credentials_path}"
            )
        except Exception as e:
            raise SheetsAuthError(f"Google Sheets API 인증 실패: {e}")

    def _with_retry(self, func, *args, **kwargs) -> Any:
        """API 호출 래퍼: Exponential Backoff 적용

        Google 권장 알고리즘: min((2^n + random_ms), max_backoff)

        Args:
            func: 호출할 함수
            *args, **kwargs: 함수 인자

        Returns:
            함수 실행 결과

        Raises:
            SheetsRateLimitError: 최대 재시도 횟수 초과
        """
        max_backoff = 64

        for attempt in range(self.max_retries):
            try:
                time.sleep(self.api_delay)
                return func(*args, **kwargs)
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit exceeded
                    wait_time = min((2**attempt) + random.uniform(0, 1), max_backoff)
                    logger.warning(f"Rate limit 초과. {wait_time:.1f}초 후 재시도 ({attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                elif e.resp.status == 403:
                    raise SheetsAuthError(f"권한 거부: {e}")
                else:
                    raise SheetsClientError(f"API 오류: {e}")

        raise SheetsRateLimitError(f"최대 재시도 횟수({self.max_retries}) 초과")

    def get_title_column(self) -> List[Tuple[int, str]]:
        """Title 열(B열) 데이터 가져오기

        Returns:
            List[Tuple[int, str]]: [(행 번호, 제목), ...]
        """
        range_name = f"{self.config.sheet_name}!{self.config.title_column}:{self.config.title_column}"

        result = self._with_retry(
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=self.config.spreadsheet_id, range=range_name)
            .execute
        )

        values = result.get("values", [])
        data = []

        # 데이터 시작 행부터 처리 (헤더 제외)
        for i, row in enumerate(values, start=1):
            if i < self.config.data_start_row:
                continue
            if row and row[0]:  # 빈 셀 제외
                data.append((i, row[0]))

        logger.info(f"시트에서 {len(data)}개 Title 로드 완료")
        return data

    def get_current_values(self, rows: List[int]) -> Dict[int, Tuple[bool, str]]:
        """지정된 행들의 현재 P열, Q열 값 가져오기

        Args:
            rows: 행 번호 목록

        Returns:
            Dict[int, Tuple[bool, str]]: {행 번호: (체크박스 값, 날짜 값)}
        """
        if not rows:
            return {}

        # P열과 Q열 범위
        min_row = min(rows)
        max_row = max(rows)
        range_name = (
            f"{self.config.sheet_name}!"
            f"{self.config.checkbox_column}{min_row}:{self.config.date_column}{max_row}"
        )

        result = self._with_retry(
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=self.config.spreadsheet_id, range=range_name)
            .execute
        )

        values = result.get("values", [])
        data = {}

        for i, row in enumerate(values, start=min_row):
            if i in rows:
                checkbox = row[0].upper() == "TRUE" if row else False
                date_val = row[1] if len(row) > 1 else ""
                data[i] = (checkbox, date_val)

        return data

    def update_row(self, row: int, checkbox_value: bool, date_value: str) -> None:
        """단일 행의 P열(체크박스)과 Q열(날짜) 업데이트

        Args:
            row: 행 번호
            checkbox_value: 체크박스 값 (True/False)
            date_value: 날짜 문자열
        """
        range_name = (
            f"{self.config.sheet_name}!"
            f"{self.config.checkbox_column}{row}:{self.config.date_column}{row}"
        )

        values = [[str(checkbox_value).upper(), date_value]]

        self._with_retry(
            self._service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self.config.spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": values},
            )
            .execute
        )

    def batch_update(self, updates: List[Dict[str, Any]]) -> int:
        """여러 행 일괄 업데이트 (P, Q, R, S 열)

        Args:
            updates: [{"row": 행번호, "checkbox": bool, "date": str, "subfolder": str, "full_path": str}, ...]

        Returns:
            int: 업데이트된 셀 수
        """
        if not updates:
            return 0

        data = []
        for update in updates:
            row = update["row"]
            # P:S 범위 (P, Q, R, S = 4개 열)
            range_name = (
                f"{self.config.sheet_name}!"
                f"{self.config.checkbox_column}{row}:{self.config.path_column}{row}"
            )

            # S열 하이퍼링크 수식 생성
            full_path = update.get("full_path", "")
            if full_path:
                # Windows 경로를 file:/// URL로 변환
                file_url = "file:///" + full_path.replace("\\", "/")
                hyperlink = f'=HYPERLINK("{file_url}", "열기")'
            else:
                hyperlink = ""

            # P, Q, R, S 순서로 4개 값
            data.append(
                {
                    "range": range_name,
                    "values": [[
                        str(update["checkbox"]).upper(),  # P열: 체크박스
                        update["date"],                    # Q열: 날짜
                        update.get("subfolder", ""),       # R열: 서브폴더
                        hyperlink                          # S열: NAS 링크
                    ]],
                }
            )

        body = {"valueInputOption": "USER_ENTERED", "data": data}

        result = self._with_retry(
            self._service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=self.config.spreadsheet_id, body=body)
            .execute
        )

        updated_cells = result.get("totalUpdatedCells", 0)
        logger.info(f"{len(updates)}개 행 업데이트 완료 ({updated_cells}개 셀)")
        return updated_cells

    def batch_update_duplicate_column(self, rows: List[int], value: bool = True) -> int:
        """중복 컬럼(T열) 일괄 업데이트

        Args:
            rows: 업데이트할 행 번호 목록
            value: 체크박스 값 (기본: True)

        Returns:
            int: 업데이트된 셀 수
        """
        if not rows:
            return 0

        data = []
        for row in rows:
            range_name = (
                f"{self.config.sheet_name}!"
                f"{self.config.duplicate_column}{row}"
            )
            data.append({
                "range": range_name,
                "values": [[str(value).upper()]]
            })

        body = {"valueInputOption": "USER_ENTERED", "data": data}

        result = self._with_retry(
            self._service.spreadsheets()
            .values()
            .batchUpdate(spreadsheetId=self.config.spreadsheet_id, body=body)
            .execute
        )

        updated_cells = result.get("totalUpdatedCells", 0)
        logger.info(f"중복 컬럼({self.config.duplicate_column}열) {len(rows)}개 행 업데이트 완료")
        return updated_cells

    def reset_duplicate_column(self, start_row: int = 2, end_row: int = None) -> int:
        """중복 컬럼(T열) 초기화

        Args:
            start_row: 시작 행 (기본: 2, 헤더 제외)
            end_row: 끝 행 (기본: None, 자동 감지)

        Returns:
            int: 초기화된 행 수
        """
        if end_row is None:
            end_row = self.get_row_count()

        if end_row < start_row:
            return 0

        range_name = (
            f"{self.config.sheet_name}!"
            f"{self.config.duplicate_column}{start_row}:{self.config.duplicate_column}{end_row}"
        )

        num_rows = end_row - start_row + 1
        values = [["FALSE"] for _ in range(num_rows)]

        self._with_retry(
            self._service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self.config.spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": values},
            )
            .execute
        )

        logger.info(f"중복 컬럼({self.config.duplicate_column}열) {num_rows}개 행 초기화 완료")
        return num_rows

    def get_row_count(self) -> int:
        """시트의 총 행 수 반환

        Returns:
            int: 총 행 수
        """
        range_name = f"{self.config.sheet_name}!A:A"

        result = self._with_retry(
            self._service.spreadsheets()
            .values()
            .get(spreadsheetId=self.config.spreadsheet_id, range=range_name)
            .execute
        )

        values = result.get("values", [])
        return len(values)

    def reset_all_rows(self, start_row: int = 2, end_row: int = None) -> int:
        """모든 행의 P열(체크박스)을 FALSE로, Q, R, S열을 비우기

        Args:
            start_row: 시작 행 (기본: 2, 헤더 제외)
            end_row: 끝 행 (기본: None, 자동 감지)

        Returns:
            int: 초기화된 행 수
        """
        if end_row is None:
            end_row = self.get_row_count()

        if end_row < start_row:
            return 0

        # P:S 전체 범위 초기화 (P, Q, R, S = 4개 열)
        range_name = (
            f"{self.config.sheet_name}!"
            f"{self.config.checkbox_column}{start_row}:{self.config.path_column}{end_row}"
        )

        # 모든 행을 FALSE, 빈 문자열로 초기화 (4개 열)
        num_rows = end_row - start_row + 1
        values = [["FALSE", "", "", ""] for _ in range(num_rows)]

        self._with_retry(
            self._service.spreadsheets()
            .values()
            .update(
                spreadsheetId=self.config.spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body={"values": values},
            )
            .execute
        )

        logger.info(f"{num_rows}개 행 초기화 완료 (P열=FALSE, Q,R,S열=빈값)")
        return num_rows

    def __str__(self) -> str:
        """클라이언트 정보 문자열 반환"""
        return f"SheetsClient(sheet={self.config.sheet_name})"
