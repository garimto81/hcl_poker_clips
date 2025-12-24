#!/usr/bin/env python
"""NAS-Google Sheets 동기화 CLI

NAS 폴더의 파일을 Google Sheets와 동기화합니다.
매칭된 행의 P열(NAS)을 TRUE로, Q열(DownloadedAt)을 오늘 날짜로 업데이트합니다.

Usage:
    python run_nas_sync.py              # 기본 동기화 실행
    python run_nas_sync.py --dry-run    # 테스트 실행 (실제 업데이트 없음)
    python run_nas_sync.py --verbose    # 상세 로그 출력
    python run_nas_sync.py --status     # 현재 상태 확인
    python run_nas_sync.py --reset      # P열/Q열 전체 초기화 후 동기화
"""

import argparse
import logging
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.sync import NASSheetsSync, SyncConfig
from src.sync.sheets_client import SheetsClient


def setup_logging(verbose: bool = False):
    """로깅 설정

    Args:
        verbose: True면 DEBUG 레벨, False면 INFO 레벨
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("nas_sync.log", encoding="utf-8"),
        ],
    )


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="NAS-Google Sheets 동기화",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_nas_sync.py              # 기본 동기화 실행
  python run_nas_sync.py --dry-run    # 테스트 실행 (업데이트 없음)
  python run_nas_sync.py --verbose    # 상세 로그 출력
  python run_nas_sync.py --status     # 현재 상태 확인
  python run_nas_sync.py --reset      # P열/Q열 전체 초기화 후 동기화

열 매핑:
  B열: Title (매칭 기준)
  P열: NAS (체크박스) -> TRUE로 변경
  Q열: DownloadedAt (날짜) -> 오늘 날짜로 변경
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="테스트 실행 (실제 업데이트 없음)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="상세 로그 출력",
    )

    parser.add_argument(
        "--status",
        action="store_true",
        help="현재 상태 확인 (동기화 실행 안함)",
    )

    parser.add_argument(
        "--nas-folder",
        type=str,
        help="NAS 폴더 경로 (기본: config.ini 설정값)",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="P열/Q열 전체 초기화 후 동기화 (기존 체크 모두 해제)",
    )

    # 유사도 매칭 옵션
    parser.add_argument(
        "--no-fuzzy",
        action="store_true",
        help="유사도 매칭 비활성화 (정확히 일치만 매칭)",
    )

    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="유사도 임계값 (0.0-1.0, 기본: 0.85)",
    )

    # 중복 감지 옵션
    parser.add_argument(
        "--no-duplicates",
        action="store_true",
        help="중복 감지 비활성화",
    )

    parser.add_argument(
        "--detect-duplicates-only",
        action="store_true",
        help="중복 감지만 실행 (동기화 없음)",
    )

    parser.add_argument(
        "--duplicate-report",
        type=str,
        default=None,
        help="중복 보고서 저장 파일 경로",
    )

    # 중복 파일 삭제 옵션
    parser.add_argument(
        "--delete-duplicates",
        action="store_true",
        help="중복 파일 자동 삭제 (기본: dry-run, --force로 실제 삭제)",
    )

    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="중복 파일 삭제만 실행 (동기화 없음)",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="확인 없이 삭제 실행 (위험!)",
    )

    parser.add_argument(
        "--cleanup-similarity",
        type=float,
        default=None,
        help="삭제용 파일명 유사도 임계값 (0.0-1.0, 기본: 0.85)",
    )

    parser.add_argument(
        "--cleanup-size-variance",
        type=float,
        default=None,
        help="삭제용 크기 차이 허용 비율 (0.0-1.0, 기본: 0.10 = 10%%)",
    )

    parser.add_argument(
        "--audit-log",
        action="store_true",
        help="삭제 감사 로그 조회",
    )

    parser.add_argument(
        "--export-audit",
        type=str,
        default=None,
        help="감사 로그 CSV 내보내기",
    )

    args = parser.parse_args()

    # 로깅 설정
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)

    try:
        # 설정 로드
        config = SyncConfig()

        # NAS 폴더 경로 오버라이드
        if args.nas_folder:
            config.nas_folder = args.nas_folder

        # 유사도 매칭 설정 오버라이드
        if args.no_fuzzy:
            config.fuzzy_enabled = False
        if args.threshold is not None:
            config.similarity_threshold = args.threshold

        # 중복 감지 설정 오버라이드
        if args.no_duplicates:
            config.duplicate_detection = False

        # 설정 유효성 검사
        config.validate()

        # 동기화 서비스 생성
        sync = NASSheetsSync(config)

        # 감사 로그 조회 모드
        if args.audit_log:
            from src.sync.matching import DeletionAuditLog

            audit = DeletionAuditLog(log_path=config.cleanup_audit_log)
            stats = audit.get_statistics()

            print("=" * 60)
            print("삭제 감사 로그 통계")
            print("=" * 60)
            print(f"총 항목 수: {stats['total_entries']}")
            print(f"삭제된 파일: {stats['files_deleted']}")
            print(f"건너뛴 파일: {stats['files_skipped']}")
            print(f"에러: {stats['errors']}")
            print(f"Dry-run 삭제: {stats['dry_run_deletions']}")
            print(f"절약된 용량: {stats['total_gb_freed']} GB")
            print(f"로그 생성일: {stats['log_created']}")
            print(f"마지막 업데이트: {stats['last_updated']}")
            print("=" * 60)

            # 최근 항목 표시
            recent = audit.get_recent_entries(limit=10)
            if recent:
                print("\n최근 10개 항목:")
                for entry in recent:
                    dry_str = "[DRY-RUN]" if entry.dry_run else ""
                    print(f"  {entry.timestamp[:19]} {entry.action:6} {dry_str} {entry.filename[:40]}")

            return 0

        # 감사 로그 CSV 내보내기
        if args.export_audit:
            from src.sync.matching import DeletionAuditLog

            audit = DeletionAuditLog(log_path=config.cleanup_audit_log)
            audit.export_csv(args.export_audit)
            print(f"감사 로그 CSV 내보내기 완료: {args.export_audit}")
            return 0

        # 중복 파일 삭제 모드
        if args.delete_duplicates or args.cleanup_only:
            from src.sync.nas_client import NASClient
            from src.sync.matching import DuplicateCleaner

            print("=" * 70)
            print("중복 파일 삭제 모드")
            print("=" * 70)

            # 설정 오버라이드
            similarity = args.cleanup_similarity or config.cleanup_similarity_threshold
            size_variance = args.cleanup_size_variance or config.cleanup_size_variance

            print(f"파일명 유사도 임계값: {similarity:.0%}")
            print(f"크기 차이 허용 범위: {size_variance:.0%}")
            print()

            # NAS 클라이언트
            nas = NASClient(config.nas_folder)
            if not nas.is_accessible():
                print(f"[ERROR] NAS 폴더에 접근할 수 없습니다: {config.nas_folder}")
                return 1

            # 파일 정보 수집
            nas_files = nas.get_files_with_dates()
            file_sizes = nas.get_file_sizes()
            print(f"NAS 파일 수: {len(nas_files)}")

            # Cleaner 초기화
            cleaner = DuplicateCleaner(
                similarity_threshold=similarity,
                size_variance_threshold=size_variance,
                audit_log_path=config.cleanup_audit_log,
            )

            # 삭제 후보 찾기
            candidates, groups = cleaner.find_cleanup_candidates(nas_files, file_sizes)

            if not candidates:
                print("\n삭제할 중복 파일이 없습니다.")
                return 0

            # 미리보기 출력
            preview = cleaner.generate_preview(candidates, groups)
            print(preview)

            # Dry-run 결정
            is_dry_run = not args.force

            if is_dry_run:
                print("\n[DRY-RUN 모드] 실제 삭제는 수행되지 않습니다.")
                print("실제로 삭제하려면 --force 옵션을 추가하세요.")
            else:
                # 확인 프롬프트
                if config.cleanup_require_confirmation:
                    confirm = input("\n'DELETE'를 입력하여 삭제를 확인하세요: ")
                    if confirm != "DELETE":
                        print("삭제가 취소되었습니다.")
                        return 0

            # 삭제 실행
            result = cleaner.cleanup(
                files=nas_files,
                file_sizes=file_sizes,
                dry_run=is_dry_run,
            )

            # 결과 출력
            print("\n" + "=" * 70)
            print("삭제 결과")
            print("=" * 70)
            print(f"분석된 파일: {result.files_analyzed}")
            print(f"중복 그룹: {result.total_groups}")
            print(f"삭제된 파일: {result.files_deleted}")
            print(f"건너뛴 파일: {result.files_skipped}")
            print(f"절약된 용량: {result.gb_freed} GB")
            print(f"에러: {len(result.errors)}")
            print(f"Dry-run: {result.dry_run}")
            print("=" * 70)

            if result.errors:
                print("\n에러 목록:")
                for filename, error in result.errors:
                    print(f"  - {filename}: {error}")

            # cleanup_only가 아니면 동기화도 실행
            if not args.cleanup_only:
                print("\n동기화 시작...")
                sync_result = sync.sync(dry_run=args.dry_run, verbose=args.verbose)
                if sync_result.errors > 0:
                    return 1

            return 0

        # 중복 감지만 실행 모드
        if args.detect_duplicates_only:
            from src.sync.nas_client import NASClient
            from src.sync.matching import DuplicateDetector

            print("=" * 60)
            print("중복 파일 감지 실행")
            print("=" * 60)

            nas = NASClient(config.nas_folder)
            if not nas.is_accessible():
                print(f"[ERROR] NAS 폴더에 접근할 수 없습니다: {config.nas_folder}")
                return 1

            nas_files = nas.get_files_with_dates()
            print(f"NAS 파일 수: {len(nas_files)}")

            detector = DuplicateDetector(threshold=config.duplicate_threshold)
            groups = detector.find_duplicates(nas_files)

            report = detector.generate_report(groups)
            print(report)

            # 보고서 파일 저장
            if args.duplicate_report:
                with open(args.duplicate_report, "w", encoding="utf-8") as f:
                    f.write(report)
                print(f"\n보고서 저장: {args.duplicate_report}")

            stats = detector.get_statistics(groups)
            print(f"\n통계: {stats}")
            return 0

        # 상태 확인 모드
        if args.status:
            print("현재 상태 확인 중...")
            status = sync.get_status()

            print("\n" + "=" * 50)
            print("시스템 상태")
            print("=" * 50)
            print(f"NAS 접근: {'가능' if status['nas_accessible'] else '불가'}")
            print(f"NAS 파일 수: {status['nas_file_count']}")
            print(f"시트 행 수: {status['sheet_row_count']}")
            print("\n설정:")
            print(status["config"])
            print("=" * 50)
            return 0

        # 초기화 모드 (--reset)
        if args.reset:
            print("=" * 60)
            print("[RESET] P열/Q열 전체 초기화 시작")
            print("=" * 60)

            sheets = SheetsClient(config)
            row_count = sheets.get_row_count()
            print(f"총 {row_count - 1}개 행 초기화 예정 (헤더 제외)")

            if not args.dry_run:
                confirm = input("정말로 초기화하시겠습니까? (y/N): ")
                if confirm.lower() != "y":
                    print("초기화 취소됨")
                    return 0

                reset_count = sheets.reset_all_rows(start_row=config.data_start_row)
                print(f"{reset_count}개 행 초기화 완료!")
            else:
                print("[DRY-RUN] 초기화 시뮬레이션 (실제 변경 없음)")

            print("=" * 60)
            print()

        # 동기화 실행
        result = sync.sync(dry_run=args.dry_run, verbose=args.verbose)

        # 결과에 따른 종료 코드
        if result.errors > 0:
            return 1
        return 0

    except ValueError as e:
        logger.error(f"설정 오류: {e}")
        print(f"\n[ERROR] 설정 오류: {e}")
        return 1

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
        return 130

    except Exception as e:
        logger.exception(f"예기치 않은 오류: {e}")
        print(f"\n[ERROR] 예기치 않은 오류: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
