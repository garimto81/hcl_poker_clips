"""매칭 유틸리티 모듈

유사도 매칭, 정규화, 중복 감지 및 정리 기능을 제공합니다.
"""

from .normalizer import FilenameNormalizer
from .fuzzy_matcher import FuzzyMatcher, MatchResult
from .duplicate_detector import DuplicateDetector, DuplicateGroup
from .duplicate_cleaner import DuplicateCleaner, DeletionCandidate, CleanupResult
from .deletion_audit import DeletionAuditLog, AuditEntry

__all__ = [
    "FilenameNormalizer",
    "FuzzyMatcher",
    "MatchResult",
    "DuplicateDetector",
    "DuplicateGroup",
    "DuplicateCleaner",
    "DeletionCandidate",
    "CleanupResult",
    "DeletionAuditLog",
    "AuditEntry",
]
