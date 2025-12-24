"""유사도 매칭 모듈

rapidfuzz 라이브러리를 사용한 유사도 기반 파일명 매칭을 제공합니다.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    from difflib import SequenceMatcher
    RAPIDFUZZ_AVAILABLE = False

from .normalizer import FilenameNormalizer


@dataclass
class MatchResult:
    """매칭 결과"""

    matched: bool                    # 매칭 성공 여부
    score: float                     # 유사도 점수 (0.0 - 1.0)
    match_type: str                  # 매칭 유형 ("exact", "normalized", "fuzzy", "none")
    original_filename: str           # 원본 파일명
    matched_title: str               # 매칭된 시트 제목
    matched_row: int                 # 매칭된 시트 행 번호
    alternatives: List[Tuple[str, float, int]] = field(default_factory=list)  # [(title, score, row), ...]


class FuzzyMatcher:
    """유사도 기반 파일명 매칭 클래스

    3단계 매칭 전략을 사용합니다:
    1. 정확히 일치 (기본 정규화 후)
    2. 표준 정규화 후 일치
    3. 유사도 매칭 (임계값 이상)
    """

    def __init__(
        self,
        threshold: float = 0.85,
        method: str = "token_sort_ratio"
    ):
        """FuzzyMatcher 초기화

        Args:
            threshold: 유사도 임계값 (0.0 - 1.0, 기본값: 0.85)
            method: 매칭 알고리즘
                   ("ratio", "partial_ratio", "token_sort_ratio", "token_set_ratio")
        """
        self.threshold = threshold
        self.method = method
        self._use_rapidfuzz = RAPIDFUZZ_AVAILABLE

    def _get_similarity(self, s1: str, s2: str) -> float:
        """두 문자열의 유사도 계산

        Args:
            s1: 첫 번째 문자열
            s2: 두 번째 문자열

        Returns:
            유사도 점수 (0.0 - 1.0)
        """
        if not s1 or not s2:
            return 0.0

        if self._use_rapidfuzz:
            if self.method == "ratio":
                return fuzz.ratio(s1, s2) / 100.0
            elif self.method == "partial_ratio":
                return fuzz.partial_ratio(s1, s2) / 100.0
            elif self.method == "token_sort_ratio":
                return fuzz.token_sort_ratio(s1, s2) / 100.0
            elif self.method == "token_set_ratio":
                return fuzz.token_set_ratio(s1, s2) / 100.0
            else:
                return fuzz.token_sort_ratio(s1, s2) / 100.0
        else:
            # difflib 폴백
            return SequenceMatcher(None, s1, s2).ratio()

    def find_best_match(
        self,
        filename: str,
        candidates: Dict[str, int],  # {normalized_title: row_num}
        original_titles: Optional[Dict[str, str]] = None  # {normalized: original}
    ) -> MatchResult:
        """파일명에 가장 적합한 제목 찾기

        3단계 매칭 전략:
        1. 기본 정규화 후 정확히 일치 (score=1.0)
        2. 표준 정규화 후 일치 (score=0.95)
        3. 공격적 정규화 + 유사도 매칭 (score >= threshold)

        Args:
            filename: NAS 파일명 (확장자 제외)
            candidates: {정규화된 제목: 행 번호} 딕셔너리
            original_titles: {정규화된 제목: 원본 제목} 딕셔너리 (선택)

        Returns:
            MatchResult: 매칭 결과
        """
        original_titles = original_titles or {}

        # 1단계: 기본 정규화 후 정확히 일치
        norm_basic = FilenameNormalizer.normalize_basic(filename)
        if norm_basic in candidates:
            return MatchResult(
                matched=True,
                score=1.0,
                match_type="exact",
                original_filename=filename,
                matched_title=original_titles.get(norm_basic, norm_basic),
                matched_row=candidates[norm_basic],
            )

        # 2단계: 표준 정규화 후 일치 (특수문자 제거)
        norm_standard = FilenameNormalizer.normalize_standard(filename)
        for title_norm, row in candidates.items():
            title_standard = FilenameNormalizer.normalize_standard(
                original_titles.get(title_norm, title_norm)
            )
            if title_standard == norm_standard:
                return MatchResult(
                    matched=True,
                    score=0.95,
                    match_type="normalized",
                    original_filename=filename,
                    matched_title=original_titles.get(title_norm, title_norm),
                    matched_row=row,
                )

        # 3단계: 공격적 정규화 후 일치 (복사본 패턴 제거)
        norm_aggressive = FilenameNormalizer.normalize_aggressive(filename)
        for title_norm, row in candidates.items():
            title_aggressive = FilenameNormalizer.normalize_aggressive(
                original_titles.get(title_norm, title_norm)
            )
            if title_aggressive == norm_aggressive:
                return MatchResult(
                    matched=True,
                    score=0.90,
                    match_type="normalized_aggressive",
                    original_filename=filename,
                    matched_title=original_titles.get(title_norm, title_norm),
                    matched_row=row,
                )

        # 4단계: 유사도 매칭
        best_score = 0.0
        best_match: Optional[Tuple[str, int]] = None
        alternatives: List[Tuple[str, float, int]] = []

        for title_norm, row in candidates.items():
            original_title = original_titles.get(title_norm, title_norm)
            title_aggressive = FilenameNormalizer.normalize_aggressive(original_title)

            score = self._get_similarity(norm_aggressive, title_aggressive)

            if score > best_score:
                best_score = score
                best_match = (title_norm, row)

            # 임계값의 90% 이상인 대안 추적
            if score >= self.threshold * 0.9:
                alternatives.append((original_title, score, row))

        # 유사도 순 정렬
        alternatives.sort(key=lambda x: x[1], reverse=True)

        if best_score >= self.threshold and best_match:
            return MatchResult(
                matched=True,
                score=best_score,
                match_type="fuzzy",
                original_filename=filename,
                matched_title=original_titles.get(best_match[0], best_match[0]),
                matched_row=best_match[1],
                alternatives=alternatives[:5],  # 상위 5개 대안
            )

        return MatchResult(
            matched=False,
            score=best_score,
            match_type="none",
            original_filename=filename,
            matched_title="",
            matched_row=-1,
            alternatives=alternatives[:5],
        )

    def batch_find_matches(
        self,
        filenames: List[str],
        candidates: Dict[str, int],
        original_titles: Optional[Dict[str, str]] = None
    ) -> List[MatchResult]:
        """여러 파일명에 대한 매칭 수행

        Args:
            filenames: 파일명 목록
            candidates: {정규화된 제목: 행 번호} 딕셔너리
            original_titles: {정규화된 제목: 원본 제목} 딕셔너리 (선택)

        Returns:
            List[MatchResult]: 각 파일명에 대한 매칭 결과
        """
        return [
            self.find_best_match(filename, candidates, original_titles)
            for filename in filenames
        ]

    @property
    def using_rapidfuzz(self) -> bool:
        """rapidfuzz 사용 여부"""
        return self._use_rapidfuzz
