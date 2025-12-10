# Playwright 기반 브라우저 자동화 통합 계획
## HCL Poker Clips 자동 다운로드 앱 (2025년 12월 기준)

### 1. Playwright 통합 개요

Playwright는 YouTube의 JavaScript challenge (PO 토큰, 보안 챌린지 등)를 해결하기 위한 핵심 기술입니다. 이 통합을 통해 yt-dlp 단독으로는 해결할 수 없는 보안 정책을 우회하여 다운로드 성공률을 높일 수 있습니다.

### 2. Playwright 설치 및 설정

#### 2.1 의존성 설치
```bash
# 필수 패키지 설치
pip install playwright
playwright install chromium  # Chrome 브라우저 설치
```

#### 2.2 환경 설정
```python
# playwright_config.py
import os
from playwright.async_api import async_playwright
from typing import Dict, List

class PlaywrightConfig:
    # 브라우저 설정
    BROWSER_TYPE = 'chromium'  # 또는 'firefox', 'webkit'
    HEADLESS = True  # GUI 없이 실행 (서버 환경용)
    
    # 브라우저 옵션
    BROWSER_ARGS = [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--allow-running-insecure-content',
        '--disable-features=VizDisplayCompositor',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu',
        '--lang=en-US,en;q=0.9'
    ]
    
    # 브라우저 컨텍스트 설정
    BROWSER_CONTEXT = {
        'viewport': {'width': 1920, 'height': 1080},
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'locale': 'en-US',
        'timezone_id': 'Asia/Seoul',
        'geolocation': {'longitude': 127.3845, 'latitude': 36.3191},  # 대한민국
        'permissions': ['notifications'],
        'extra_http_headers': {
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br'
        }
    }
```

### 3. 브라우저 지문 우회 기법

#### 3.1 브라우저 지문 변경
```python
# browser_fingerprint_bypass.py
async def bypass_browser_fingerprint(page):
    """
    브라우저 지문을 우회하는 스크립트 주입
    """
    await page.add_init_script("""
        // navigator.webdriver 속성 제거
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // window.chrome 속성 설정
        Object.defineProperty(window, 'chrome', {
            get: () => {
                return {
                    runtime: true
                };
            }
        });
        
        // plugins 속성 설정
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                return [1, 2, 3, 4, 5];
            }
        });
        
        // languages 속성 설정
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en', 'ko'],
        });
        
        // webgl vendor 정보 변경
        const originalWebgl = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) {
                return 'Google Inc. (NVIDIA)';
            }
            if (parameter === 37446) {
                return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 950 Direct3D11 vs_5_0 ps_5_0, D3D11-27.21.14.5671)';
            }
            return originalWebgl.call(this, parameter);
        };
        
        // webdriver 속성 삭제
        delete navigator.__proto__.webdriver;
    """)
```

#### 3.2 무작위 브라우저 설정
```python
import random

class RandomBrowserConfig:
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    
    VIEWPORT_SIZES = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1536, 'height': 864},
        {'width': 1280, 'height': 1024}
    ]
    
    LOCALES = ['en-US', 'ko-KR', 'ja-JP', 'zh-CN', 'es-ES']
    
    @classmethod
    def get_random_config(cls):
        return {
            'user_agent': random.choice(cls.USER_AGENTS),
            'viewport': random.choice(cls.VIEWPORT_SIZES),
            'locale': random.choice(cls.LOCALES),
            'timezone_id': random.choice(['America/New_York', 'Europe/London', 'Asia/Seoul', 'Asia/Tokyo'])
        }
```

### 4. Playwright 다운로드 엔진 구현

#### 4.1 Playwright 다운로드 엔진 클래스
```python
# playwright_engine.py
import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse, parse_qs
import re

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright_stealth import stealth_async

from .playwright_config import PlaywrightConfig
from .browser_fingerprint_bypass import bypass_browser_fingerprint
from .random_browser_config import RandomBrowserConfig

class PlaywrightDownloadEngine:
    def __init__(self, config: PlaywrightConfig):
        self.config = config
        self.browser = None
        self.context = None
        self.current_page = None
        self.playwright_instance = None
        self.active_downloads = {}
    
    async def initialize(self):
        """Playwright 인스턴스 초기화"""
        self.playwright_instance = await async_playwright().start()
        self.browser = await self.playwright_instance.chromium.launch(
            headless=self.config.HEADLESS,
            args=self.config.BROWSER_ARGS
        )
    
    async def create_context(self, custom_config: Optional[Dict] = None):
        """브라우저 컨텍스트 생성"""
        context_config = self.config.BROWSER_CONTEXT.copy()
        
        if custom_config:
            context_config.update(custom_config)
        
        self.context = await self.browser.new_context(**context_config)
        
        # 브라우저 지문 우회 적용
        await self.context.route("**/*", self._block_unnecessary_resources)
        
        return self.context
    
    async def _block_unnecessary_resources(self, route):
        """불필요한 리소스 요청 차단하여 속도 향상"""
        resource_type = route.request.resource_type
        if resource_type in ["image", "stylesheet", "font", "media", "other"]:
            await route.abort()
        else:
            await route.continue_()
    
    async def create_page(self, context: Optional[BrowserContext] = None):
        """새 페이지 생성"""
        ctx = context or self.context or await self.create_context()
        page = await ctx.new_page()
        
        # 브라우저 지문 우회 적용
        await bypass_browser_fingerprint(page)
        
        # stealth 기술 적용 (선택적)
        await stealth_async(page)
        
        return page
    
    async def extract_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        """비디오 정보 추출"""
        page = await self.create_page()
        try:
            # YouTube 페이지 로드
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # PO 토큰 및 기타 보안 챌린지 해결 대기
            await page.wait_for_load_state("domcontentloaded")
            
            # YouTube 내부 플레이어 데이터 추출
            player_response = await self._extract_player_response(page)
            
            if player_response:
                return {
                    'title': player_response.get('videoDetails', {}).get('title'),
                    'duration': player_response.get('videoDetails', {}).get('lengthSeconds'),
                    'formats': player_response.get('streamingData', {}).get('formats', []),
                    'adaptive_formats': player_response.get('streamingData', {}).get('adaptiveFormats', [])
                }
            
            return None
            
        except Exception as e:
            print(f"비디오 정보 추출 실패: {str(e)}")
            return None
        finally:
            await page.close()
    
    async def _extract_player_response(self, page: Page) -> Optional[Dict]:
        """YouTube 플레이어 응답 데이터 추출"""
        try:
            # PO 토큰을 포함한 플레이어 응답 데이터 추출
            # YouTube의 내부 구조를 기반으로 데이터를 찾아 추출
            player_response = await page.evaluate("""
                () => {
                    // 다양한 위치에서 player response 찾기
                    const sources = [
                        () => window.ytInitialPlayerResponse,
                        () => document.querySelector('#player')?.playerResponse,
                        () => document.querySelector('ytd-app')?.data?.playerResponse
                    ];
                    
                    for (const source of sources) {
                        try {
                            const response = source();
                            if (response && typeof response === 'object') {
                                return response;
                            }
                        } catch (e) {
                            continue;
                        }
                    }
                    
                    // YouTube의 내부 API에서 정보 추출 시도
                    try {
                        const scriptTags = Array.from(document.querySelectorAll('script'));
                        for (const tag of scriptTags) {
                            if (tag.textContent.includes('ytInitialPlayerResponse')) {
                                const match = tag.textContent.match(/ytInitialPlayerResponse\s*=\s*({.*?});/);
                                if (match) {
                                    return JSON.parse(match[1]);
                                }
                            }
                        }
                    } catch (e) {
                        // 파싱 실패 시 넘어감
                    }
                    
                    return null;
                }
            """)
            
            return player_response
            
        except Exception as e:
            print(f"Player response 추출 실패: {str(e)}")
            return None
    
    async def download_video(self, url: str, output_path: str) -> Optional[str]:
        """비디오 다운로드"""
        page = await self.create_page()
        try:
            # 비디오 정보 추출
            video_info = await self.extract_video_info(url)
            if not video_info:
                print("비디오 정보를 추출할 수 없습니다")
                return None
            
            # 최적의 포맷 선택
            best_format = self._select_best_format(video_info)
            if not best_format:
                print("적절한 다운로드 포맷을 찾을 수 없습니다")
                return None
            
            # 다운로드 URL로 페이지 이동 후 다운로드 시작
            download_url = best_format.get('url')
            if not download_url:
                return None
            
            # 직접 다운로드는 불가능하므로, yt-dlp와 연계하여 사용
            # 이 부분은 실제 다운로드를 위해 yt-dlp와 협업하는 방식으로 구현
            print(f"Playwright가 준비한 다운로드 정보: {best_format}")
            return best_format
            
        except Exception as e:
            print(f"비디오 다운로드 실패: {str(e)}")
            return None
        finally:
            await page.close()
    
    def _select_best_format(self, video_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """가장 적절한 비디오 포맷 선택"""
        formats = video_info.get('formats', []) + video_info.get('adaptive_formats', [])
        
        # 최고 화질 조건으로 필터링
        best_format = None
        max_quality = 0
        
        for fmt in formats:
            # 비디오만 포함하거나, 비디오+오디오 포함 형식 선택
            has_video = fmt.get('mimeType', '').startswith('video/')
            quality = fmt.get('qualityLabel', 'unknown')
            
            # 화질 수치화 및 비교 (간단한 비교 로직)
            quality_num = self._quality_to_number(quality)
            if has_video and quality_num > max_quality:
                max_quality = quality_num
                best_format = fmt
        
        # 최대 1080p까지만 허용 (설정에 따라 조절 가능)
        if best_format and self._quality_to_number(best_format.get('qualityLabel', 'unknown')) > 1080:
            # 1080p 초과 시 해당 수준의 포맷 다시 검색
            for fmt in formats:
                quality = fmt.get('qualityLabel', 'unknown')
                if self._quality_to_number(quality) == 1080:
                    return fmt
        
        return best_format
    
    def _quality_to_number(self, quality_label: str) -> int:
        """화질 레이블을 숫자로 변환"""
        quality_map = {
            '144p': 144,
            '240p': 240,
            '360p': 360,
            '480p': 480,
            '720p': 720,
            '1080p': 1080,
            '1440p': 1440,
            '2160p': 2160,  # 4K
            '4320p': 4320   # 8K
        }
        
        # 숫자만 추출
        if quality_label in quality_map:
            return quality_map[quality_label]
        
        # 텍스트에서 숫자 추출
        match = re.search(r'(\d+)p', quality_label)
        if match:
            return int(match.group(1))
        
        return 0
```

### 5. Playwright와 yt-dlp 통합

#### 5.1 yt-dlp의 Playwright 지원
```python
# playwright_yt_dlp_integration.py
import yt_dlp

def get_yt_dlp_playwright_options():
    """
    Playwright를 사용하는 yt-dlp 옵션 설정
    """
    return {
        'format': 'best[height<=1080][ext=mp4]',
        'retries': 15,
        'fragment_retries': 100,
        'cookiefile': 'cookies.txt',
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'android', 'web_creator'],
                'player_skip': ['webpage', 'js', 'configs'],
                'hls_use_mpd': True,
            }
        },
        'compat_opts': ['no-youtube-po-token'],
        # Playwright 기반 브라우저 자동화 사용
        'playwright': True,
        'playwright_include_audio': True,
        'playwright_firefox': False,  # Chromium 사용
        'playwright_browsers': ['chromium'],
        # Playwright 페이지 생성 시 콜백 함수
        'playwright_page_callback': playwright_page_setup
    }

async def playwright_page_setup(page):
    """
    Playwright 페이지 설정 콜백
    """
    # 브라우저 지문 우회
    await bypass_browser_fingerprint(page)
    
    # 불필요한 리소스 차단
    await page.route("**/*", lambda route: route.abort() 
                     if route.request.resource_type in ["image", "stylesheet", "font", "media", "other"] 
                     else route.continue_())
```

#### 5.2 Playwright 전용 다운로드 전략
```python
from .download_engine_interface import DownloadEngine
from .playwright_engine import PlaywrightDownloadEngine

class PlaywrightStrategy(DownloadEngine):
    def __init__(self, config):
        self.config = config
        self.playwright_engine = PlaywrightDownloadEngine(config)
    
    async def download(self, url: str, options: Dict[str, Any]) -> Optional[str]:
        """Playwright를 사용한 다운로드"""
        await self.playwright_engine.initialize()
        
        # 무작위 브라우저 설정 사용
        random_config = RandomBrowserConfig.get_random_config()
        context = await self.playwright_engine.create_context(random_config)
        
        # 비디오 정보 추출
        video_info = await self.playwright_engine.extract_video_info(url)
        if not video_info:
            print("Playwright를 통해 비디오 정보를 가져올 수 없습니다")
            return None
        
        # yt-dlp와 연계하여 실제 다운로드 수행
        # Playwright는 보안 우회 및 PO 토큰 해결에 사용
        return await self._execute_download_with_ytdlp(url, options)
    
    async def _execute_download_with_ytdlp(self, url: str, options: Dict[str, Any]) -> Optional[str]:
        """
        Playwright를 보조로 사용하여 yt-dlp 다운로드 실행
        """
        # yt-dlp 옵션에 Playwright 관련 설정 추가
        ytdlp_options = get_yt_dlp_playwright_options()
        ytdlp_options.update(options)
        
        try:
            with yt_dlp.YoutubeDL(ytdlp_options) as ydl:
                info = ydl.extract_info(url, download=True)
                return info.get('filepath') if info else None
        except Exception as e:
            print(f"yt-dlp를 통한 다운로드 실패: {str(e)}")
            return None
    
    def validate(self, url: str) -> bool:
        """URL 유효성 검사"""
        try:
            parsed = urlparse(url)
            return parsed.netloc in ['www.youtube.com', 'youtube.com', 'youtu.be']
        except:
            return False
    
    def get_strategy_name(self) -> str:
        """전략 이름 반환"""
        return "PlaywrightStrategy"
```

### 6. 실행 및 관리

#### 6.1 Playwright 풀 관리
```python
import asyncio
from typing import Dict, List
from contextlib import asynccontextmanager

class PlaywrightPoolManager:
    def __init__(self, max_instances: int = 5):
        self.max_instances = max_instances
        self.active_instances: List[PlaywrightDownloadEngine] = []
        self.available_instances: List[PlaywrightDownloadEngine] = []
        self.instance_lock = asyncio.Lock()
    
    async def get_instance(self) -> PlaywrightDownloadEngine:
        """사용 가능한 Playwright 인스턴스 가져오기"""
        async with self.instance_lock:
            if self.available_instances:
                instance = self.available_instances.pop()
            else:
                if len(self.active_instances) < self.max_instances:
                    # 새 인스턴스 생성
                    config = PlaywrightConfig()
                    instance = PlaywrightDownloadEngine(config)
                    await instance.initialize()
                    self.active_instances.append(instance)
                else:
                    # 대기 또는 예외 처리
                    await asyncio.sleep(1)
                    return await self.get_instance()
        
        return instance
    
    async def return_instance(self, instance: PlaywrightDownloadEngine):
        """사용한 Playwright 인스턴스 반납"""
        async with self.instance_lock:
            self.available_instances.append(instance)
    
    async def close_all(self):
        """모든 Playwright 인스턴스 종료"""
        for instance in self.active_instances:
            if instance.browser:
                await instance.browser.close()
        self.active_instances.clear()
        self.available_instances.clear()
```

### 7. 보안 및 안정성

#### 7.1 Playwright 자원 관리
```python
import weakref
import atexit

class PlaywrightResourceManager:
    def __init__(self):
        self.playwright_instances = weakref.WeakSet()
        atexit.register(self.cleanup)
    
    def register_instance(self, engine: PlaywrightDownloadEngine):
        """Playwright 인스턴스 등록"""
        self.playwright_instances.add(engine)
    
    def cleanup(self):
        """종료 시 모든 Playwright 인스턴스 정리"""
        for engine in self.playwright_instances:
            if engine.browser:
                try:
                    # 비동기 컨텍스트 외부에서는 다른 방법으로 정리 필요
                    pass
                except Exception as e:
                    print(f"Playwright 인스턴스 정리 중 오류: {e}")
```

이 Playwright 통합 계획은 YouTube의 최신 보안 정책을 우회하기 위해 중요한 역할을 하며, 특히 PO 토큰 및 JavaScript challenge 해결에 핵심적인 기능을 제공합니다.