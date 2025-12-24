"""중복 파일 감지 모듈

NAS 파일 간의 중복을 감지하고 관리합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from .normalizer import FilenameNormalizer
from .fuzzy_matcher import FuzzyMatcher


@dataclass
class DuplicateGroup:
    """중복 파일 그룹"""

    canonical_name: str                              # 정규화된 핵심 이름
    files: List[Tuple[str, str, datetime, int]]     # [(original_name, path, mtime, size), ...]
    similarity_scores: List[float]                   # 각 파일의 유사도 점수
    recommended: Optional[str] = None                # 유지 권장 파일명 (최신)
    duplicates_to_mark: List[str] = field(default_factory=list)  # 중복으로 표시할 파일들

    def __len__(self) -> int:
        return len(self.files)


class DuplicateDetector:
    """중복 파일 감지 클래스

    파일명 유사도를 기반으로 중복 파일을 감지합니다.
    """

    def __init__(
        self,
        threshold: float = 0.95,
    ):
        """DuplicateDetector 초기화

        Args:
            threshold: 중복 판정 유사도 임계값 (0.0 - 1.0, 기본값: 0.95)
        """
        self.threshold = threshold
        self.matcher = FuzzyMatcher(threshold=threshold)

    def find_duplicates(
        self,
        files: Dict[str, Tuple[str, datetime, str, str]],  # {normalized: (original, mtime, subfolder, path)}
        file_sizes: Optional[Dict[str, int]] = None,  # {original_name: size_in_bytes}
    ) -> List[DuplicateGroup]:
        """중복 파일 그룹 찾기

        Args:
            files: NASClient.get_files_with_dates()의 반환값
            file_sizes: 파일 크기 매핑 (optional) - {원본_파일명: 크기(bytes)}

        Returns:
            List[DuplicateGroup]: 중복 그룹 목록
        """
        groups: List[DuplicateGroup] = []
        processed: Set[str] = set()
        sizes = file_sizes or {}

        file_list = list(files.items())

        for i, (norm1, (orig1, mtime1, subfolder1, path1)) in enumerate(file_list):
            if norm1 in processed:
                continue

            # 핵심 제목 추출 (복사본 접미사 제거)
            core1 = FilenameNormalizer.normalize_aggressive(orig1)
            size1 = sizes.get(orig1, 0)

            # 유사한 파일 찾기
            group_files: List[Tuple[str, str, datetime, int]] = [(orig1, path1, mtime1, size1)]
            group_scores: List[float] = [1.0]

            for j, (norm2, (orig2, mtime2, subfolder2, path2)) in enumerate(file_list[i + 1:], start=i + 1):
                if norm2 in processed:
                    continue

                core2 = FilenameNormalizer.normalize_aggressive(orig2)

                # 유사도 계산
                score = self.matcher._get_similarity(core1, core2)

                if score >= self.threshold:
                    size2 = sizes.get(orig2, 0)
                    group_files.append((orig2, path2, mtime2, size2))
                    group_scores.append(score)
                    processed.add(norm2)

            # 2개 이상인 경우만 중복 그룹으로 처리
            if len(group_files) > 1:
                processed.add(norm1)

                group = DuplicateGroup(
                    canonical_name=core1,
                    files=group_files,
                    similarity_scores=group_scores,
                )

                # 최신 파일 결정 (유지 권장)
                newest_idx = max(range(len(group_files)), key=lambda x: group_files[x][2])
                group.recommended = group_files[newest_idx][0]

                # 중복으로 표시할 파일 결정 (최신 제외)
                group.duplicates_to_mark = [
                    f[0] for idx, f in enumerate(group_files)
                    if idx != newest_idx
                ]

                groups.append(group)

        return groups

    def get_duplicates_to_mark(
        self,
        files: Dict[str, Tuple[str, datetime, str, str]]
    ) -> Set[str]:
        """중복으로 표시할 파일명 집합 반환

        각 중복 그룹에서 최신 파일을 제외한 나머지를 반환합니다.

        Args:
            files: NASClient.get_files_with_dates()의 반환값

        Returns:
            Set[str]: 중복으로 표시할 파일명 집합
        """
        groups = self.find_duplicates(files)
        duplicates: Set[str] = set()

        for group in groups:
            duplicates.update(group.duplicates_to_mark)

        return duplicates

    def generate_report(self, groups: List[DuplicateGroup]) -> str:
        """중복 보고서 생성

        Args:
            groups: 중복 그룹 목록

        Returns:
            포맷된 보고서 문자열
        """
        if not groups:
            return "중복 파일이 발견되지 않았습니다."

        lines = ["=" * 60]
        lines.append(f"중복 파일 보고서: {len(groups)}개 그룹 발견")
        lines.append("=" * 60)
        lines.append("")

        total_duplicates = sum(len(g.duplicates_to_mark) for g in groups)
        lines.append(f"총 중복 파일 수: {total_duplicates}개")
        lines.append("")

        for i, group in enumerate(groups, 1):
            lines.append(f"그룹 {i}: {group.canonical_name[:50]}...")
            lines.append("-" * 40)

            for (name, path, mtime, size), score in zip(group.files, group.similarity_scores):
                marker = " [유지]" if name == group.recommended else " [중복]"
                date_str = mtime.strftime('%Y-%m-%d')
                lines.append(f"  - {name[:60]}")
                lines.append(f"    날짜: {date_str}, 유사도: {score:.2f}{marker}")

            lines.append("")

        return "\n".join(lines)

    def get_statistics(self, groups: List[DuplicateGroup]) -> Dict:
        """중복 통계 반환

        Args:
            groups: 중복 그룹 목록

        Returns:
            통계 딕셔너리
        """
        if not groups:
            return {
                "total_groups": 0,
                "total_files_in_groups": 0,
                "total_duplicates": 0,
                "files_to_keep": 0,
            }

        total_files = sum(len(g.files) for g in groups)
        total_duplicates = sum(len(g.duplicates_to_mark) for g in groups)

        return {
            "total_groups": len(groups),
            "total_files_in_groups": total_files,
            "total_duplicates": total_duplicates,
            "files_to_keep": total_files - total_duplicates,
        }
