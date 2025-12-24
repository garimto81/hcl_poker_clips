"""파일명 정규화 유틸리티

파일명을 여러 수준으로 정규화하여 유사도 매칭을 지원합니다.
"""

import re
import unicodedata
from typing import Tuple


class FilenameNormalizer:
    """파일명 정규화 클래스

    여러 수준의 정규화를 제공하여 유사도 매칭 정확도를 높입니다.
    """

    # 복사본 패턴 (파일명 끝에 붙는 패턴)
    COPY_PATTERNS = [
        r'\s*\(\d+\)$',           # (1), (2) 등
        r'\s*_\d+$',              # _1, _2 등
        r'\s*-\d+$',              # -1, -2 등
        r'\s*\(copy\)$',          # (copy)
        r'\s*_copy$',             # _copy
        r'\s*\s+copy$',           # space + copy
        r'\s*\[duplicate\]$',     # [duplicate]
    ]

    # YouTube Video ID 패턴 (11자 영숫자+특수문자)
    YOUTUBE_ID_PATTERN = r'\s*\[[A-Za-z0-9_-]{11}\]$'

    # 확장자/포맷 코드 패턴
    FORMAT_CODE_PATTERN = r'\.f\d{3}$'  # .f399, .f140 등

    # 제거할 특수문자 (공백 제외)
    SPECIAL_CHARS = r'[-_!@#$%^&*()+=\[\]{};:\'",.<>/?\\|`~]'

    @classmethod
    def normalize_basic(cls, text: str) -> str:
        """기본 정규화: 소문자 + 공백 제거

        현재 시스템에서 사용하는 정규화 방식입니다.

        Args:
            text: 원본 텍스트

        Returns:
            정규화된 문자열
        """
        return text.lower().replace(" ", "").strip()

    @classmethod
    def remove_youtube_id(cls, text: str) -> str:
        """YouTube Video ID 제거

        파일명 끝에 붙는 [xxxxxxxxxxx] 형태의 ID를 제거합니다.

        Args:
            text: 원본 텍스트

        Returns:
            YouTube ID가 제거된 문자열
        """
        # YouTube ID 패턴 제거
        text = re.sub(cls.YOUTUBE_ID_PATTERN, '', text)
        # 포맷 코드 제거 (.f399 등)
        text = re.sub(cls.FORMAT_CODE_PATTERN, '', text)
        return text.strip()

    @classmethod
    def normalize_standard(cls, text: str) -> str:
        """표준 정규화: 소문자 + 모든 특수문자 및 공백 제거

        특수문자 차이로 인한 매칭 실패를 방지합니다.
        YouTube ID와 포맷 코드도 제거합니다.

        Args:
            text: 원본 텍스트

        Returns:
            정규화된 문자열
        """
        # YouTube ID 및 포맷 코드 먼저 제거
        text = cls.remove_youtube_id(text)
        # Unicode 정규화 (NFD -> NFC)
        text = unicodedata.normalize('NFKC', text)
        # 모든 특수문자 제거
        text = re.sub(cls.SPECIAL_CHARS, '', text)
        # 모든 공백 제거
        text = re.sub(r'\s+', '', text)
        return text.lower().strip()

    @classmethod
    def normalize_aggressive(cls, text: str) -> str:
        """공격적 정규화: 복사본 패턴도 제거

        (1), _copy 등의 복사본 접미사를 제거하여
        원본과 복사본을 같은 파일로 인식합니다.

        Args:
            text: 원본 텍스트

        Returns:
            정규화된 문자열
        """
        # 먼저 복사본 패턴 제거
        for pattern in cls.COPY_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        # 그 다음 표준 정규화 적용
        return cls.normalize_standard(text)

    @classmethod
    def extract_core_title(cls, text: str) -> Tuple[str, str]:
        """핵심 제목과 접미사 분리

        복사본 접미사를 분리하여 반환합니다.

        Args:
            text: 원본 텍스트

        Returns:
            Tuple[str, str]: (핵심 제목, 제거된 접미사)
        """
        suffix = ""

        for pattern in cls.COPY_PATTERNS:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                suffix = match.group()
                text = text[:match.start()]
                break

        return text.strip(), suffix

    @classmethod
    def remove_channel_suffix(cls, text: str) -> str:
        """채널 접미사 제거

        @Hustler Casino Live 같은 채널명 접미사를 제거합니다.

        Args:
            text: 원본 텍스트

        Returns:
            채널명이 제거된 문자열
        """
        # @로 시작하는 채널명 패턴
        patterns = [
            r'\s*@\s*Hustler\s*Casino\s*Live\s*$',
            r'\s*@\s*HustlerCasinoLive\s*$',
            r'\s*@\s*[A-Za-z0-9_]+\s*$',  # 일반 채널명
        ]

        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        return text.strip()

    @classmethod
    def get_all_normalizations(cls, text: str) -> dict:
        """모든 정규화 버전 반환

        디버깅 및 분석용으로 모든 정규화 버전을 반환합니다.

        Args:
            text: 원본 텍스트

        Returns:
            dict: 각 정규화 수준별 결과
        """
        core_title, suffix = cls.extract_core_title(text)

        return {
            "original": text,
            "basic": cls.normalize_basic(text),
            "standard": cls.normalize_standard(text),
            "aggressive": cls.normalize_aggressive(text),
            "no_channel": cls.remove_channel_suffix(text),
            "core_title": core_title,
            "suffix": suffix,
        }
