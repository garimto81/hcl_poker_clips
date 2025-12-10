"""
HCL Poker Clips 다운로더 설정 파일
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional, List


class Config:
    """설정 클래스"""
    
    # 기본 설정
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "downloads")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", "1.0"))
    REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", "3.0"))
    
    # YouTube 관련 설정
    YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@HCLPokerClips/videos"
    
    # yt-dlp 설정
    YTDLP_OPTIONS = {
        'outtmpl': os.getenv("OUTTMPL", '%(title)s.%(ext)s'),
        'quiet': os.getenv("YTDLP_QUIET", "False").lower() == "true",
        'no_warnings': os.getenv("YTDLP_NO_WARNINGS", "False").lower() == "true",
        'ignoreerrors': os.getenv("YTDLP_IGNORE_ERRORS", "False").lower() == "true",  # 오류 무시 비활성화
        'extractaudio': os.getenv("YTDLP_EXTRACT_AUDIO", "False").lower() == "true",
        'download_archive': os.getenv("YTDLP_ARCHIVE", "downloaded.txt"),
        'format': os.getenv("YTDLP_FORMAT", "best[height<=1080][ext=mp4]"),  # 1080p 이하 MP4 화질
        'retries': int(os.getenv("YTDLP_RETRIES", "10")),  # 재시도 횟수 증가
        'fragment_retries': int(os.getenv("YTDLP_FRAGMENT_RETRIES", "50")),
        'file_access_retries': int(os.getenv("YTDLP_FILE_ACCESS_RETRIES", "10")),
        'sleep_interval_requests': float(os.getenv("SLEEP_INTERVAL_REQUESTS", "5.0")),
        'max_sleep_interval': float(os.getenv("MAX_SLEEP_INTERVAL", "15.0")),
        'extractor_args': {
            'youtube': {
                'skip': ['authcheck'],
                'player_client': ['android', 'web_creator', 'web_embedded', 'android_creator'],  # 더 많은 클라이언트 시도
                'player_skip': ['webpage', 'js', 'configs'],  # JS 로직 스킵
                'hls_use_mpd': True,  # MPD 기반 HLS 사용
            }
        },
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
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
        'youtube_include_dash_manifest': True,
        'youtube_include_hls_manifest': True,
        'extractor_retries': 10,
        'retry_sleep_functions': {
            'http_error': 'lambda x: 5 * x',  # 지수 백오프
            'connection': 'lambda x: 5 * x',
            'auth': 'lambda x: 10 * x',
        },
        'cookiefile': 'cookies.txt',  # 쿠키 파일 사용
        'check_formats': 'selected',  # 선택한 포맷만 확인
        'geo_bypass': True,  # 지리적 제한 우회
        'compat_opts': ['no-live-chat', 'no-youtube-channel-identification', 'no-youtube-po-token'],  # 호환성 옵션
        'live_from_start': False,
        # 외부 다운로더 설정
        'external_downloader': {
            'youtube': 'ffmpeg',
        },
        'external_downloader_args': {
            'ffmpeg': ['-c', 'copy', '-bsf:a', 'aac_adtstoasc'],
        },
        # 브라우저 기반 추출 설정 (JavaScript challenge 해결을 위해)
        'extractor_retries': 10,
        'extractor_args': {
            'youtube': {
                'player_client': ['web'],
                'player_skip': ['webpage', 'js', 'configs'],
                'hls_use_mpd': True,
            }
        },
        # 브라우저 기반 추출 설정을 위한 호환 옵션
        'compat_opts': ['no-live-chat', 'no-youtube-channel-identification', 'no-youtube-po-token', 'youtube-include-hls-dash-manifests'],
    }
    
    # 회피 전략 관련 설정
    AVOIDANCE_STRATEGY = {
        'use_random_user_agent': os.getenv("USE_RANDOM_USER_AGENT", "True").lower() == "true",
        'random_delay': os.getenv("RANDOM_DELAY", "True").lower() == "true",
        'max_delay_seconds': float(os.getenv("MAX_DELAY_SECONDS", "15.0")),
        'min_delay_seconds': float(os.getenv("MIN_DELAY_SECONDS", "5.0")),
        'use_proxy': os.getenv("USE_PROXY", "False").lower() == "true",
        'proxy_list': os.getenv("PROXY_LIST", "").split(",") if os.getenv("PROXY_LIST") else [],
    }
    
    # 로깅 설정
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "hcl_poker_clips_downloader.log")
    
    # 일정 설정
    DAILY_RUN_TIME = os.getenv("DAILY_RUN_TIME", "09:00")  # 24시간 형식 (예: 09:00)

    # 수동 URL 추가 기능
    MANUAL_URL_FILE = os.getenv("MANUAL_URL_FILE", "manual_urls.txt")

    @classmethod
    def get_download_dir(cls) -> Path:
        """다운로드 디렉토리 경로 반환"""
        download_path = Path(cls.DOWNLOAD_DIR)
        download_path.mkdir(exist_ok=True)
        return download_path

    @classmethod
    def get_ytdlp_options(cls) -> Dict[str, Any]:
        """yt-dlp 옵션 반환"""
        options = cls.YTDLP_OPTIONS.copy()
        options['outtmpl'] = str(cls.get_download_dir() / options['outtmpl'])
        options['download_archive'] = str(cls.get_download_dir() / options['download_archive'])
        return options

    @classmethod
    def get_avoidance_strategy(cls) -> Dict[str, Any]:
        """회피 전략 설정 반환"""
        return cls.AVOIDANCE_STRATEGY.copy()

    @classmethod
    def get_manual_urls(cls) -> List[str]:
        """수동으로 추가된 URL 목록을 파일에서 가져옴"""
        urls = []
        manual_urls_path = Path(cls.MANUAL_URL_FILE)
        if manual_urls_path.exists():
            with open(manual_urls_path, 'r', encoding='utf-8') as f:
                for line in f:
                    url = line.strip()
                    if url and url.startswith('http'):
                        urls.append(url)
        return urls


def load_config_from_file(config_path: Optional[str] = None) -> Config:
    """
    파일에서 설정 로드
    설정 파일이 없으면 기본 설정 사용
    """
    if config_path and os.path.exists(config_path):
        # 설정 파일이 있는 경우, 해당 파일에서 환경변수 설정
        import configparser
        config_parser = configparser.ConfigParser()
        config_parser.read(config_path)
        
        # 설정 파일의 값을 환경변수로 설정
        for section_name in config_parser.sections():
            for key, value in config_parser.items(section_name):
                if not os.getenv(key.upper()):
                    os.environ[key.upper()] = value
    
    return Config()