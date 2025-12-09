"""
HCL Poker Clips 다운로더 테스트 스크립트

이 스크립트는 HCL Poker Clips 다운로더의 기본 기능을 테스트합니다.
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
src_dir = str(project_root / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from src.utils.youtube_utils import YouTubeUtils, get_hcl_poker_clips_videos
from src.config.config import Config
from src.download.main import HCLPokerClipsDownloader


def test_youtube_utils():
    """YouTube 유틸리티 함수 테스트"""
    print("1. YouTube 유틸리티 테스트 시작...")
    
    utils = YouTubeUtils()
    
    # HCL Poker Clips 채널 URL 테스트
    channel_url = "https://www.youtube.com/@HCLPokerClips/videos"
    print(f"채널 URL: {channel_url}")
    
    # 동영상 URL 추출 테스트
    print("동영상 URL 추출 중...")
    video_urls = utils.get_video_urls_from_channel(channel_url)
    print(f"찾은 동영상 수: {len(video_urls)}")
    
    if video_urls:
        print(f"첫 번째 동영상 URL: {video_urls[0]}")
        
        # 첫 번째 동영상 정보 가져오기 테스트
        video_info = utils.get_video_info(video_urls[0])
        if video_info:
            print(f"제목: {video_info.get('title', 'N/A')}")
            print(f"ID: {video_info.get('id', 'N/A')}")
            print(f"길이: {video_info.get('duration', 'N/A')} 초")
    
    print("YouTube 유틸리티 테스트 완료.\n")


def test_config():
    """설정 모듈 테스트"""
    print("2. 설정 모듈 테스트 시작...")
    
    config = Config()
    print(f"다운로드 디렉토리: {config.DOWNLOAD_DIR}")
    print(f"최대 재시도 횟수: {config.MAX_RETRIES}")
    print(f"채널 URL: {config.YOUTUBE_CHANNEL_URL}")
    
    print("yt-dlp 옵션:")
    ytdlp_opts = config.get_ytdlp_options()
    for key, value in list(ytdlp_opts.items())[:5]:  # 처음 5개 항목만 출력
        print(f"  {key}: {value}")
    
    print("설정 모듈 테스트 완료.\n")


def test_downloader():
    """다운로더 클래스 테스트"""
    print("3. 다운로더 클래스 테스트 시작...")
    
    # 설정 로드
    config = Config()
    
    # 다운로더 생성
    downloader = HCLPokerClipsDownloader(config=config)
    
    print(f"채널 URL: {downloader.channel_url}")
    print(f"다운로드 디렉토리: {downloader.download_dir}")
    print(f"최대 재시도 횟수: {downloader.max_retries}")
    
    print("다운로더 클래스 테스트 완료.\n")


def main():
    """메인 테스트 함수"""
    print("HCL Poker Clips 다운로더 테스트를 시작합니다.\n")
    
    try:
        test_youtube_utils()
        test_config()
        test_downloader()
        
        print("모든 테스트가 완료되었습니다.")
        print("\n다운로더를 실행하시려면 'python run_downloader.py' 명령을 사용하세요.")
        
    except Exception as e:
        print(f"테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()