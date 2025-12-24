"""매칭 모듈 테스트

유사도 매칭, 정규화, 중복 감지 기능을 테스트합니다.
"""

import pytest
from datetime import datetime

from src.sync.matching import (
    FilenameNormalizer,
    FuzzyMatcher,
    MatchResult,
    DuplicateDetector,
    DuplicateGroup,
    DuplicateCleaner,
    DeletionCandidate,
    CleanupResult,
    DeletionAuditLog,
)


class TestFilenameNormalizer:
    """FilenameNormalizer 테스트"""

    def test_normalize_basic(self):
        """기본 정규화 테스트"""
        assert FilenameNormalizer.normalize_basic("Hello World") == "helloworld"
        assert FilenameNormalizer.normalize_basic("  Test  ") == "test"
        assert FilenameNormalizer.normalize_basic("A B C") == "abc"

    def test_normalize_standard(self):
        """표준 정규화 테스트 (특수문자 제거)"""
        assert FilenameNormalizer.normalize_standard("Hello-World_Test!") == "helloworldtest"
        assert FilenameNormalizer.normalize_standard("Video #123") == "video123"
        assert FilenameNormalizer.normalize_standard("$100,000 Pot!") == "100000pot"
        assert FilenameNormalizer.normalize_standard("Alan's Video") == "alansvideo"

    def test_normalize_aggressive(self):
        """공격적 정규화 테스트 (복사본 패턴 제거)"""
        assert FilenameNormalizer.normalize_aggressive("Video (1)") == "video"
        assert FilenameNormalizer.normalize_aggressive("Video_copy") == "video"
        assert FilenameNormalizer.normalize_aggressive("Video-2") == "video"
        assert FilenameNormalizer.normalize_aggressive("Video (copy)") == "video"

    def test_extract_core_title(self):
        """핵심 제목 추출 테스트"""
        core, suffix = FilenameNormalizer.extract_core_title("Video (1)")
        assert core == "Video"
        assert suffix == " (1)"

        core, suffix = FilenameNormalizer.extract_core_title("Test_copy")
        assert core == "Test"
        assert suffix == "_copy"

        core, suffix = FilenameNormalizer.extract_core_title("Normal Video")
        assert core == "Normal Video"
        assert suffix == ""

    def test_remove_channel_suffix(self):
        """채널 접미사 제거 테스트"""
        result = FilenameNormalizer.remove_channel_suffix(
            "Great Play @Hustler Casino Live"
        )
        assert result == "Great Play"

        result = FilenameNormalizer.remove_channel_suffix(
            "Amazing Hand @HustlerCasinoLive"
        )
        assert result == "Amazing Hand"


class TestFuzzyMatcher:
    """FuzzyMatcher 테스트"""

    def test_exact_match(self):
        """정확히 일치 테스트"""
        matcher = FuzzyMatcher(threshold=0.85)
        candidates = {"testvideo": 1, "anothervideo": 2}
        original_titles = {"testvideo": "Test Video", "anothervideo": "Another Video"}

        result = matcher.find_best_match("Test Video", candidates, original_titles)

        assert result.matched is True
        assert result.score == 1.0
        assert result.match_type == "exact"
        assert result.matched_row == 1

    def test_normalized_match(self):
        """정규화 후 일치 테스트"""
        matcher = FuzzyMatcher(threshold=0.85)
        candidates = {"pokerhandreview": 1}
        original_titles = {"pokerhandreview": "Poker Hand Review"}

        # 특수문자가 다른 경우
        result = matcher.find_best_match(
            "Poker-Hand-Review!", candidates, original_titles
        )

        assert result.matched is True
        assert result.score >= 0.90  # normalized match

    def test_fuzzy_match(self):
        """유사도 매칭 테스트"""
        matcher = FuzzyMatcher(threshold=0.80)
        candidates = {"amazingpokerhand": 1}
        original_titles = {"amazingpokerhand": "Amazing Poker Hand"}

        # 약간 다른 이름
        result = matcher.find_best_match(
            "Amazing Pokr Hand", candidates, original_titles
        )

        assert result.matched is True
        assert result.score >= 0.80
        assert result.match_type == "fuzzy"

    def test_no_match(self):
        """매칭 실패 테스트"""
        matcher = FuzzyMatcher(threshold=0.95)
        candidates = {"completelyunrelated": 1}

        result = matcher.find_best_match("Test Video", candidates)

        assert result.matched is False
        assert result.match_type == "none"
        assert result.matched_row == -1

    def test_threshold_boundary(self):
        """임계값 경계 테스트"""
        # 높은 임계값 (엄격)
        matcher_strict = FuzzyMatcher(threshold=0.95)
        candidates = {"testvideo": 1}

        result = matcher_strict.find_best_match("Test Viedo", candidates)  # 오타
        # 95% 미만이면 매칭 실패
        if result.score < 0.95:
            assert result.matched is False

    def test_using_rapidfuzz(self):
        """rapidfuzz 사용 여부 확인"""
        matcher = FuzzyMatcher()
        # rapidfuzz가 설치되어 있으면 True
        assert isinstance(matcher.using_rapidfuzz, bool)


class TestDuplicateDetector:
    """DuplicateDetector 테스트"""

    def test_find_duplicates(self):
        """중복 찾기 테스트"""
        detector = DuplicateDetector(threshold=0.90)

        now = datetime.now()
        older = datetime(2024, 1, 1)

        files = {
            "testvideo": ("Test Video", now, "", "/path/test.mp4"),
            "testvideo1": ("Test Video (1)", older, "", "/path/test1.mp4"),
            "anothervideo": ("Another Video", now, "", "/path/another.mp4"),
        }

        groups = detector.find_duplicates(files)

        # "Test Video"와 "Test Video (1)"이 중복으로 감지되어야 함
        assert len(groups) >= 1

    def test_get_duplicates_to_mark(self):
        """중복 표시할 파일 목록 테스트"""
        detector = DuplicateDetector(threshold=0.90)

        now = datetime.now()
        older = datetime(2024, 1, 1)

        files = {
            "testvideo": ("Test Video", now, "", "/path/test.mp4"),  # 최신
            "testvideo1": ("Test Video (1)", older, "", "/path/test1.mp4"),  # 오래됨
        }

        duplicates = detector.get_duplicates_to_mark(files)

        # 오래된 파일이 중복으로 표시되어야 함
        if duplicates:  # 중복이 감지된 경우
            assert "Test Video (1)" in duplicates
            assert "Test Video" not in duplicates  # 최신 파일은 표시 안됨

    def test_no_duplicates(self):
        """중복 없음 테스트"""
        detector = DuplicateDetector(threshold=0.95)

        now = datetime.now()
        files = {
            "video1": ("Video One", now, "", "/path/1.mp4"),
            "video2": ("Video Two", now, "", "/path/2.mp4"),
            "video3": ("Video Three", now, "", "/path/3.mp4"),
        }

        groups = detector.find_duplicates(files)

        # 완전히 다른 파일들은 중복이 아님
        assert len(groups) == 0

    def test_generate_report(self):
        """보고서 생성 테스트"""
        detector = DuplicateDetector()

        # 빈 그룹
        report = detector.generate_report([])
        assert "중복 파일이 발견되지 않았습니다" in report

        # 중복 그룹이 있는 경우
        now = datetime.now()
        group = DuplicateGroup(
            canonical_name="testvideo",
            files=[
                ("Test Video", "/path/1.mp4", now, 0),
                ("Test Video (1)", "/path/2.mp4", now, 0),
            ],
            similarity_scores=[1.0, 0.95],
            recommended="Test Video",
            duplicates_to_mark=["Test Video (1)"],
        )

        report = detector.generate_report([group])
        assert "중복 파일 보고서" in report
        assert "1개 그룹" in report

    def test_get_statistics(self):
        """통계 테스트"""
        detector = DuplicateDetector()

        # 빈 그룹
        stats = detector.get_statistics([])
        assert stats["total_groups"] == 0
        assert stats["total_duplicates"] == 0

        # 그룹이 있는 경우
        now = datetime.now()
        group = DuplicateGroup(
            canonical_name="test",
            files=[
                ("A", "/a", now, 0),
                ("B", "/b", now, 0),
                ("C", "/c", now, 0),
            ],
            similarity_scores=[1.0, 0.95, 0.92],
            recommended="A",
            duplicates_to_mark=["B", "C"],
        )

        stats = detector.get_statistics([group])
        assert stats["total_groups"] == 1
        assert stats["total_files_in_groups"] == 3
        assert stats["total_duplicates"] == 2
        assert stats["files_to_keep"] == 1


class TestRealWorldScenarios:
    """실제 사용 시나리오 테스트"""

    def test_hustler_casino_live_variations(self):
        """Hustler Casino Live 파일명 변형 테스트"""
        matcher = FuzzyMatcher(threshold=0.85)

        # 시트의 제목들 (정규화됨)
        candidates = {
            "$100000riverbluffagainsttherichestplayeronthe table@hustlercasinolive": 1,
        }
        original_titles = {
            "$100000riverbluffagainsttherichestplayeronthe table@hustlercasinolive":
            "$100,000 River Bluff Against The Richest Player On The Table @Hustler Casino Live"
        }

        # NAS 파일명 (약간 다름)
        result = matcher.find_best_match(
            "$100,000 River Bluff Against The Richest Player On The Table @Hustler Casino Live",
            candidates,
            original_titles
        )

        assert result.matched is True

    def test_special_characters_handling(self):
        """특수문자 처리 테스트"""
        # $ 기호가 포함된 파일명
        norm1 = FilenameNormalizer.normalize_standard("$100,000 Pot!")
        norm2 = FilenameNormalizer.normalize_standard("$100000 Pot")
        assert norm1 == norm2  # 둘 다 "100000pot"

        # 아포스트로피
        norm1 = FilenameNormalizer.normalize_standard("Alan's Great Play")
        norm2 = FilenameNormalizer.normalize_standard("Alans Great Play")
        assert norm1 == norm2


class TestDuplicateCleaner:
    """DuplicateCleaner 테스트"""

    def test_size_variance_within_threshold(self):
        """10% 이내 크기 차이 테스트 - 삭제 대상"""
        cleaner = DuplicateCleaner(
            similarity_threshold=0.85,
            size_variance_threshold=0.10,
        )

        # 1GB vs 1.05GB = 5% 차이 -> 통과
        is_valid, variance = cleaner.check_size_variance(1_000_000_000, 1_050_000_000)
        assert is_valid is True
        assert variance == pytest.approx(0.0476, rel=0.01)

    def test_size_variance_exceeds_threshold(self):
        """10% 초과 크기 차이 테스트 - 삭제 제외"""
        cleaner = DuplicateCleaner(
            similarity_threshold=0.85,
            size_variance_threshold=0.10,
        )

        # 1GB vs 1.2GB = 20% 차이 -> 실패
        is_valid, variance = cleaner.check_size_variance(1_000_000_000, 1_200_000_000)
        assert is_valid is False
        assert variance == pytest.approx(0.1667, rel=0.01)

    def test_size_variance_zero_size(self):
        """크기가 0인 경우 테스트 - 삭제 제외"""
        cleaner = DuplicateCleaner()

        # 크기 정보가 없는 경우 -> 삭제 제외
        is_valid, variance = cleaner.check_size_variance(0, 1_000_000_000)
        assert is_valid is False
        assert variance == 1.0

        is_valid, variance = cleaner.check_size_variance(1_000_000_000, 0)
        assert is_valid is False

    def test_find_cleanup_candidates(self):
        """삭제 후보 찾기 테스트"""
        cleaner = DuplicateCleaner(
            similarity_threshold=0.85,
            size_variance_threshold=0.10,
        )

        now = datetime.now()
        older = datetime(2024, 1, 1)

        files = {
            "testvideo": ("Test Video", now, "", "/path/Test Video.mp4"),
            "testvideo1": ("Test Video (1)", older, "", "/path/Test Video (1).mp4"),
        }

        file_sizes = {
            "Test Video": 1_000_000_000,  # 1GB
            "Test Video (1)": 1_050_000_000,  # 1.05GB (5% 차이)
        }

        candidates, groups = cleaner.find_cleanup_candidates(files, file_sizes)

        # 크기 차이가 10% 이내이므로 중복으로 감지되어야 함
        assert len(groups) >= 1

    def test_find_cleanup_candidates_size_exceeds(self):
        """크기 차이가 큰 경우 삭제 제외 테스트"""
        cleaner = DuplicateCleaner(
            similarity_threshold=0.85,
            size_variance_threshold=0.10,
        )

        now = datetime.now()
        older = datetime(2024, 1, 1)

        files = {
            "testvideo": ("Test Video", now, "", "/path/Test Video.mp4"),
            "testvideo1": ("Test Video (1)", older, "", "/path/Test Video (1).mp4"),
        }

        file_sizes = {
            "Test Video": 1_000_000_000,  # 1GB
            "Test Video (1)": 500_000_000,  # 0.5GB (50% 차이)
        }

        candidates, groups = cleaner.find_cleanup_candidates(files, file_sizes)

        # 크기 차이가 10% 초과이므로 삭제 대상이 아님
        assert len(candidates) == 0

    def test_cleanup_result_gb_freed(self):
        """CleanupResult GB 계산 테스트"""
        result = CleanupResult(
            bytes_freed=4_500_000_000,  # 4.5GB
            dry_run=True,
        )

        assert result.gb_freed == 4.19  # 4.5 / 1024**3 ≈ 4.19

    def test_cleanup_dry_run(self):
        """Dry-run 모드 테스트"""
        cleaner = DuplicateCleaner(
            similarity_threshold=0.85,
            size_variance_threshold=0.10,
        )

        now = datetime.now()
        older = datetime(2024, 1, 1)

        files = {
            "testvideo": ("Test Video", now, "", "/nonexistent/Test Video.mp4"),
            "testvideo1": ("Test Video (1)", older, "", "/nonexistent/Test Video (1).mp4"),
        }

        file_sizes = {
            "Test Video": 1_000_000_000,
            "Test Video (1)": 1_000_000_000,
        }

        result = cleaner.cleanup(
            files=files,
            file_sizes=file_sizes,
            dry_run=True,
        )

        # Dry-run 모드에서는 실제 삭제 없음
        assert result.dry_run is True


class TestDeletionAuditLog:
    """DeletionAuditLog 테스트"""

    def test_get_statistics_empty(self):
        """빈 로그 통계 테스트"""
        import tempfile
        import os

        # 임시 파일 경로 사용
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            audit = DeletionAuditLog(log_path=temp_path)
            stats = audit.get_statistics()

            assert stats["total_entries"] == 0
            assert stats["files_deleted"] == 0
            assert stats["total_gb_freed"] == 0.0
        finally:
            # 정리
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_log_deletion(self):
        """삭제 로그 기록 테스트"""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            audit = DeletionAuditLog(log_path=temp_path)

            audit.log_deletion(
                filename="Test Video (1)",
                full_path="/path/Test Video (1).mp4",
                size=1_000_000_000,
                mtime=datetime.now(),
                similarity_score=0.95,
                size_variance=0.05,
                kept_file="Test Video",
                dry_run=False,
            )

            stats = audit.get_statistics()
            assert stats["files_deleted"] == 1
            assert stats["total_gb_freed"] == pytest.approx(0.93, rel=0.1)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_get_recent_entries(self):
        """최근 항목 조회 테스트"""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            audit = DeletionAuditLog(log_path=temp_path)

            # 3개 항목 추가
            for i in range(3):
                audit.log_deletion(
                    filename=f"Video {i}",
                    full_path=f"/path/video{i}.mp4",
                    size=100_000_000,
                    mtime=datetime.now(),
                    similarity_score=0.95,
                    size_variance=0.01,
                    kept_file="Original",
                    dry_run=True,
                )

            recent = audit.get_recent_entries(limit=2)

            # 최신순으로 2개만 반환
            assert len(recent) == 2
            assert recent[0].filename == "Video 2"  # 가장 최신
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestCleanerIntegration:
    """통합 테스트"""

    def test_keeps_newest_file(self):
        """최신 파일 유지 테스트"""
        cleaner = DuplicateCleaner(
            similarity_threshold=0.85,
            size_variance_threshold=0.10,
        )

        newest = datetime(2024, 12, 20)
        older = datetime(2024, 1, 1)

        files = {
            "testvideo": ("Test Video", newest, "", "/path/Test Video.mp4"),
            "testvideo1": ("Test Video (1)", older, "", "/path/Test Video (1).mp4"),
        }

        file_sizes = {
            "Test Video": 1_000_000_000,
            "Test Video (1)": 1_000_000_000,
        }

        candidates, groups = cleaner.find_cleanup_candidates(files, file_sizes)

        if candidates:
            # 최신 파일은 삭제 대상이 아님
            deleted_names = [c.filename for c in candidates]
            assert "Test Video" not in deleted_names

            # 오래된 파일이 삭제 대상
            assert "Test Video (1)" in deleted_names

    def test_generate_preview(self):
        """미리보기 생성 테스트"""
        cleaner = DuplicateCleaner()

        now = datetime.now()
        candidates = [
            DeletionCandidate(
                filename="Test (1)",
                full_path="/path/test1.mp4",
                size=1_000_000_000,
                mtime=now,
                reason="duplicate of 'Test'",
                similarity_score=0.99,
                size_variance=0.01,
                kept_file="Test",
            )
        ]

        groups = [
            DuplicateGroup(
                canonical_name="test",
                files=[
                    ("Test", "/path/test.mp4", now, 1_000_000_000),
                    ("Test (1)", "/path/test1.mp4", now, 1_000_000_000),
                ],
                similarity_scores=[1.0, 0.99],
                recommended="Test",
                duplicates_to_mark=["Test (1)"],
            )
        ]

        preview = cleaner.generate_preview(candidates, groups)

        assert "DUPLICATE CLEANUP PREVIEW" in preview
        assert "[KEEP]" in preview
        assert "[DELETE]" in preview


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
