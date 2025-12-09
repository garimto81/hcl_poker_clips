"""
YouTube 관련 유틸리티 함수들
회피 전략이 포함된 동영상 검색 및 URL 추출 기능
"""

import time
import random
import logging
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs
import xml.etree.ElementTree as ET
import requests

import yt_dlp
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class YouTubeUtils:
    """YouTube 관련 유틸리티 클래스"""

    def __init__(self):
        self.ua = UserAgent()

    def get_channel_id_from_url(self, channel_url: str) -> Optional[str]:
        """URL에서 채널 ID 추출 - RSS 피드 용도"""
        try:
            # URL에서 채널 ID 추출 시도
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'skip_download': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                if info and 'id' in info and 'webpage_url_basename' in info:
                    if info['webpage_url_basename'] == 'channel':
                        return info['id']
                    elif info['webpage_url_basename'] == 'user':
                        # 사용자 채널인 경우
                        return info['id']
                    elif info['webpage_url_basename'] == 'c':
                        # 커뮤니티 채널인 경우
                        return info['id']

            # yt-dlp로 안 될 경우 정규식 사용
            parsed = urlparse(channel_url)
            path_parts = parsed.path.strip('/').split('/')
            if len(path_parts) >= 2:
                if path_parts[0] in ['channel', 'user', 'c']:
                    return path_parts[1]

        except Exception as e:
            logger.warning(f"URL에서 채널 ID 추출 실패: {str(e)}")

        return None

    def get_video_urls_from_rss(self, channel_url: str) -> List[str]:
        """RSS 피드를 사용하여 동영상 URL 목록 가져오기"""
        logger.info(f"RSS 피드를 통해 동영상 URL 추출 시도: {channel_url}")

        try:
            # 채널 ID 추출
            channel_id = self.get_channel_id_from_url(channel_url)

            if channel_id:
                rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            else:
                # URL에서 직접 채널 이름 추출 시도
                parsed = urlparse(channel_url)
                path_parts = parsed.path.strip('/').split('/')
                if path_parts and path_parts[0] == '@':
                    # @HCLPokerClips 형식 처리
                    rss_url = f"https://www.youtube.com/feeds/videos.xml?user={path_parts[1]}"
                else:
                    raise ValueError("채널 ID 또는 사용자 이름을 찾을 수 없습니다")

            # RSS 피드 요청
            headers = {'User-Agent': self.ua.random}
            response = requests.get(rss_url, headers=headers)
            response.raise_for_status()

            # XML 파싱
            root = ET.fromstring(response.content)

            # 네임스페이스 정의
            namespaces = {
                'yt': 'http://www.youtube.com/xml/schemas/2015',
                'atom': 'http://www.w3.org/2005/Atom'
            }

            # 동영상 URL 목록 추출
            video_urls = []
            for entry in root.findall('atom:entry', namespaces):
                link_element = entry.find('atom:link', namespaces)
                if link_element is not None:
                    href = link_element.get('href')
                    if href and href.startswith('https://www.youtube.com/watch'):
                        video_urls.append(href)

            logger.info(f"RSS 피드를 통해 {len(video_urls)}개의 동영상 URL을 찾았습니다.")
            return video_urls

        except Exception as e:
            logger.error(f"RSS 피드를 통한 동영상 URL 추출 실패: {str(e)}")
            return []

    def get_video_urls_from_channel(self, channel_url: str) -> List[str]:
        """
        채널 URL에서 동영상 URL 목록을 추출
        다양한 방법 시도 (RSS 피드, yt-dlp 등)
        """
        logger.info(f"채널에서 동영상 URL 추출 시작: {channel_url}")

        # 1. 우선 RSS 피드 시도
        video_urls = self.get_video_urls_from_rss(channel_url)
        if video_urls:
            return video_urls

        # 2. yt-dlp를 사용한 방식 시도 (회피 전략 강화)
        try:
            # 회피 전략: 요청 간격 조절
            time.sleep(random.uniform(3, 8))

            # yt-dlp 옵션 설정 - 플레이리스트(채널)의 모든 동영상 정보 가져오기
            # 회피 전략을 최대한 적용
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': 'in_playlist',  # 플레이리스트의 동영상 목록만 추출
                'skip_download': True,
                'ignoreerrors': True,
                'sleep_interval_requests': random.uniform(2, 5),  # 요청 간 대기
                'max_sleep_interval': 10,  # 요청 간 최대 대기 시간
                'sleep_interval': random.uniform(3, 7),      # 요청 간 기본 대기 시간
                'sleep_interval_subtitles': random.uniform(1, 3),
                'extractor_args': {
                    'youtube': {
                        'skip': ['authcheck'],  # 인증 점프 건너뛰기
                        'player_skip': ['js'],  # JS 해석 건너뛰기 시도
                    }
                },
                'user_agent': self.ua.random,  # 랜덤 사용자 에이전트 설정
                'headers': {
                    'User-Agent': self.ua.random,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                }
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 채널 정보 추출
                info = ydl.extract_info(channel_url, download=False)

                # 채널 내의 동영상 URL 목록 추출
                video_urls = []
                if info and 'entries' in info:
                    for entry in info['entries']:
                        if entry and 'webpage_url' in entry:
                            video_urls.append(entry['webpage_url'])

                if video_urls:
                    logger.info(f"yt-dlp를 통해 {len(video_urls)}개의 동영상 URL을 찾았습니다.")
                    return video_urls

        except Exception as e:
            logger.error(f"yt-dlp를 사용한 채널에서 동영상 URL 추출 중 오류 발생: {str(e)}")

            # 3. 예비 방식: 더 간단한 정보만 추출
            try:
                # 다시 한번 대기 시간을 길게 설정
                time.sleep(random.uniform(5, 10))

                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,  # 간단한 정보만 추출
                    'skip_download': True,
                    'ignoreerrors': True,
                    'max_sleep_interval': 15,
                    'sleep_interval': random.uniform(5, 10),
                    'extractor_args': {
                        'youtube': {
                            'skip': ['authcheck'],
                        }
                    },
                    'user_agent': self.ua.random,
                    'headers': {
                        'User-Agent': self.ua.random,
                    }
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(channel_url, download=False)

                    if info and 'entries' in info:
                        # 엔트리가 있으면 URL을 추출 시도
                        video_urls = []
                        for entry in info['entries']:
                            if entry and 'webpage_url' in entry:
                                video_urls.append(entry['webpage_url'])
                        if video_urls:
                            logger.info(f"예비 방식으로 {len(video_urls)}개의 동영상 URL을 찾았습니다.")
                            return video_urls
                    elif info and 'webpage_url' in info:
                        # 채널 자체 URL인 경우
                        return [info['webpage_url']]
                    else:
                        return []

            except Exception as e2:
                logger.error(f"예비 방식으로도 동영상 URL 추출 실패: {str(e2)}")

        return []

    def extract_video_id(self, url: str) -> Optional[str]:
        """URL에서 동영상 ID 추출"""
        parsed = urlparse(url)
        if parsed.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com'):
            return parse_qs(parsed.query).get('v', [None])[0]
        elif parsed.hostname in ('youtu.be', 'www.youtu.be'):
            return parsed.path[1:]
        return None

    def check_video_availability(self, video_url: str) -> bool:
        """동영상의 유효성 확인"""
        try:
            # 회피 전략: 요청 간격 조절
            time.sleep(random.uniform(1, 3))

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'simulate': True,  # 실제로 다운로드하지 않고 정보만 가져옴
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return info is not None

        except Exception as e:
            logger.warning(f"동영상 확인 실패 {video_url}: {str(e)}")
            return False

    def get_video_info(self, video_url: str) -> Optional[Dict]:
        """동영상 정보 가져오기"""
        try:
            # 회피 전략: 요청 간격 조절
            time.sleep(random.uniform(2, 5))

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'simulate': True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return {
                    'id': info.get('id'),
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'upload_date': info.get('upload_date'),
                    'view_count': info.get('view_count'),
                    'thumbnail': info.get('thumbnail'),
                    'webpage_url': info.get('webpage_url')
                }

        except Exception as e:
            logger.error(f"동영상 정보 가져오기 실패 {video_url}: {str(e)}")
            return None


# 테스트 채널 URL에 대한 동영상 추출 함수
def get_hcl_poker_clips_videos() -> List[str]:
    """HCL Poker Clips 채널에서 동영상 URL 목록을 가져옴"""
    utils = YouTubeUtils()
    channel_url = "https://www.youtube.com/@HCLPokerClips/videos"
    return utils.get_video_urls_from_channel(channel_url)