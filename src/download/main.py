"""
HCL Poker Clips YouTube 동영상 자동 다운로드 앱
메인 다운로드 스크립트
"""

import os
import sys
import logging
from pathlib import Path
from typing import List, Optional
import yt_dlp

from src.utils.youtube_utils import YouTubeUtils
from src.config.config import Config

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.getenv("LOG_FILE", 'hcl_poker_clips_downloader.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HCLPokerClipsDownloader:
    """
    HCL Poker Clips 유튜브 채널 동영상 다운로더 클래스
    채널 URL: https://www.youtube.com/@HCLPokerClips/videos
    """

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.channel_url = self.config.YOUTUBE_CHANNEL_URL
        self.download_dir = self.config.get_download_dir()
        self.max_retries = self.config.MAX_RETRIES
        self.youtube_utils = YouTubeUtils()
        self.setup_directories()

    def setup_directories(self):
        """다운로드 디렉토리 설정"""
        self.download_dir.mkdir(exist_ok=True)
        logger.info(f"다운로드 디렉토리 설정됨: {self.download_dir}")

    def get_channel_videos(self) -> List[str]:
        """
        HCL Poker Clips 채널의 동영상 URL 목록을 가져옴
        회피 전략을 고려하여 구현
        """
        logger.info(f"채널에서 동영상 목록을 가져오는 중: {self.channel_url}")

        # 1. 수동으로 추가된 URL이 있는지 확인
        manual_urls = self.config.get_manual_urls()
        if manual_urls:
            logger.info(f"수동으로 추가된 {len(manual_urls)}개의 URL이 있습니다.")
            # 수동 URL을 먼저 시도하고, 채널 URL에서 가져온 것과 합침
            channel_videos = self.youtube_utils.get_video_urls_from_channel(self.channel_url)
            all_urls = list(set(manual_urls + channel_videos))  # 중복 제거
            logger.info(f"수동 URL과 채널에서 가져온 URL을 합쳐 총 {len(all_urls)}개의 URL이 준비되었습니다.")
            return all_urls
        else:
            # 2. 수동 URL이 없으면 채널에서만 가져옴
            channel_videos = self.youtube_utils.get_video_urls_from_channel(self.channel_url)
            logger.info(f"채널에서 {len(channel_videos)}개의 동영상 URL을 찾았습니다.")
            return channel_videos

    def download_video(self, video_url: str, output_filename: Optional[str] = None) -> bool:
        """
        지정된 URL의 동영상을 다운로드
        회피 전략 적용
        """
        logger.info(f"동영상 다운로드 시작: {video_url}")

        # yt-dlp 옵션 설정
        ydl_opts = self.config.get_ytdlp_options()

        # 추가 회피 전략 적용 - 기존 설정을 덮어쓰지 않도록 주의
        additional_opts = {
            'extractor_args': {
                'youtube': {
                    'skip': ['authcheck'],
                    'player_skip': ['js', 'configs', 'webpage'],
                }
            },
            'headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Referer': 'https://www.youtube.com/',
                'Origin': 'https://www.youtube.com',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            },
            'force_ipv4': True,  # IPv4만 사용
        }

        # ydl_opts에 additional_opts를 업데이트하되, 기존 설정을 유지
        for key, value in additional_opts.items():
            if isinstance(value, dict) and key in ydl_opts and isinstance(ydl_opts[key], dict):
                # 중첩된 딕셔너리의 경우, 병합
                ydl_opts[key].update(value)
            else:
                # 단순한 값의 경우, 덮어씀
                ydl_opts[key] = value

        try:
            # 회피 전략 적용: 사용자 에이전트 무작위 설정 등
            # 추가적인 회피 전략은 필요에 따라 옵션에 추가할 수 있음
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=True)

                # 제목 정보가 있는지 확인
                if info and info.get('title'):
                    logger.info(f"동영상 다운로드 완료: {info['title']}")
                else:
                    logger.info(f"동영상 다운로드 완료: {video_url}")

            return True

        except Exception as e:
            logger.error(f"동영상 다운로드 실패: {video_url}, 오류: {str(e)}")

            # 재시도 로직
            retry_count = 0
            while retry_count < self.max_retries:
                try:
                    logger.info(f"다운로드 재시도 {retry_count + 1}/{self.max_retries}")

                    # 회피 전략 추가: 요청 간격 조절
                    import time
                    import random

                    # 설정에서 정의한 시간 범위 내에서 무작위 대기
                    min_delay = self.config.AVOIDANCE_STRATEGY['min_delay_seconds']
                    max_delay = self.config.AVOIDANCE_STRATEGY['max_delay_seconds']
                    time.sleep(random.uniform(min_delay, max_delay))

                    # 재시도 시 추가 회피 전략 적용
                    retry_opts = ydl_opts.copy()
                    retry_opts['user_agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
                    retry_opts['sleep_interval'] = 5  # 재시도 시 더 긴 지연 시간

                    with yt_dlp.YoutubeDL(retry_opts) as ydl:
                        info = ydl.extract_info(video_url, download=True)

                        # 제목 정보가 있는지 확인
                        if info and info.get('title'):
                            logger.info(f"재시도로 동영상 다운로드 성공: {info['title']}")
                        else:
                            logger.info(f"재시도로 동영상 다운로드 성공: {video_url}")

                        return True

                except Exception as retry_e:
                    retry_count += 1
                    logger.error(f"재시도 실패 {retry_count}/{self.max_retries}: {str(retry_e)}")

                    if retry_count >= self.max_retries:
                        logger.error(f"모든 재시도 실패: {video_url}")

            return False

    def download_all_videos(self):
        """모든 동영상 다운로드"""
        logger.info("모든 동영상 다운로드 시작")
        video_urls = self.get_channel_videos()

        if not video_urls:
            logger.warning("다운로드할 동영상을 찾을 수 없습니다.")
            return

        for i, video_url in enumerate(video_urls, 1):
            logger.info(f"다운로드 진행 중 ({i}/{len(video_urls)}): {video_url}")
            success = self.download_video(video_url)
            if success:
                logger.info(f"다운로드 성공: {video_url}")
            else:
                logger.warning(f"다운로드 실패: {video_url}")

        logger.info("모든 동영상 다운로드 완료")

    def run_daily_download(self):
        """일일 자동 다운로드 실행"""
        logger.info("일일 자동 다운로드 시작")
        # 새로운 동영상만 다운로드하는 로직 구현
        # download_archive 옵션을 사용하여 중복 다운로드 방지
        self.download_all_videos()


def main():
    """메인 실행 함수"""
    logger.info("HCL Poker Clips 동영상 다운로더 시작")

    # 설정 로드
    config = Config()

    # 다운로더 생성
    downloader = HCLPokerClipsDownloader(config=config)

    # 일일 다운로드 실행
    downloader.run_daily_download()

    logger.info("HCL Poker Clips 동영상 다운로더 종료")


if __name__ == "__main__":
    main()