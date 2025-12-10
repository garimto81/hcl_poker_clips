# YouTube 동영상 다운로드 시스템 기술 아키텍처
## HCL Poker Clips 자동 다운로드 앱 (2025년 12월 기준)

### 1. 시스템 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                사용자 인터페이스                                  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │   GUI 앱    │ │  웹 인터페이스  │ │  CLI 도구   │ │  모바일 앱   │           │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             요청 관리 및 라우팅                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                        Request Manager                                  │ │
│  │  - 요청 큐 관리                                                           │ │
│  │  - 요청 우선순위 설정                                                     │ │
│  │  - 중복 요청 방지                                                         │ │
│  │  - 요청 분배 및 라우팅                                                    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        다운로드 전략 선택기                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      Strategy Selector                                  │ │
│  │  - 전략 평가 및 선택 알고리즘                                               │ │
│  │  - 성공률 기반 전략 우선순위 조정                                           │ │
│  │  - 실패 시 자동 전략 전환                                                  │ │
│  │  - 전략별 성능 모니터링                                                    │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        회피 전략 관리 시스템                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      Evasion Manager                                    │ │
│  │  - IP 프록시 회전 시스템                                                  │ │
│  │  - 브라우저 지문 무작위화 시스템                                            │ │
│  │  - 요청 간격 조절 시스템                                                  │ │
│  │  - 헤더 및 쿠키 관리 시스템                                               │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        다운로드 엔진 레지스트리                                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────┐ │
│  │   yt-dlp 엔진    │ │ Playwright 엔진 │ │   API 엔진      │ │  HTTP 엔진  │ │
│  │   (v2025.12+)   │ │  (v1.50+)      │ │  (비공식 API)   │ │ (직접 요청) │ │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           결과 및 오류 처리                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                    Result Manager                                       │ │
│  │  - 다운로드 성공/실패 기록                                               │ │
│  │  - 다운로드 파일 저장 및 관리                                             │ │
│  │  - 오류 분석 및 로깅                                                     │ │
│  │  - 자동 복구 및 재시도                                                   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          저장소 및 데이터베이스                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                   Data Storage                                          │ │
│  │  - 다운로드된 파일 저장소                                                 │ │
│  │  - 작업 이력 데이터베이스                                                 │ │
│  │  - 쿠키 및 인증 정보 저장소                                               │ │
│  │  - 시스템 설정 및 구성 정보                                              │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. 핵심 컴포넌트 상세 설계

#### 2.1 전략 선택기 (Strategy Selector)
```python
class StrategySelector:
    def __init__(self):
        self.strategies = [
            'YTDLPCookieStrategy',
            'PlaywrightStrategy',
            'APIBasedStrategy',
            'HTTPRequestStrategy'
        ]
        self.strategy_performance = {}
    
    def select_strategy(self, url: str, context: dict) -> str:
        # 성공률 기반 전략 선택
        # 실패한 전략 우선순위 낮춤
        # 최신 성공률 반영
        pass
    
    def update_strategy_performance(self, strategy_name: str, success: bool, time_taken: float):
        # 전략 성능 업데이트
        pass
```

#### 2.2 다운로드 엔진 인터페이스
```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class DownloadEngine(ABC):
    @abstractmethod
    async def download(self, url: str, options: Dict[str, Any]) -> Optional[str]:
        """다운로드 실행 및 파일 경로 반환"""
        pass
    
    @abstractmethod
    def validate(self, url: str) -> bool:
        """URL 유효성 검사"""
        pass
    
    @abstractmethod
    def get_strategy_name(self) -> str:
        """전략 이름 반환"""
        pass
```

#### 2.3 yt-dlp 엔진 구현
```python
class YTDLPCookieStrategy(DownloadEngine):
    def __init__(self, config):
        self.config = config
        self.options = {
            'format': self.config.YTDLP_FORMAT,
            'retries': self.config.YTDLP_RETRIES,
            'fragment_retries': self.config.YTDLP_FRAGMENT_RETRIES,
            'cookiefile': self.config.COOKIE_FILE,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web', 'android', 'web_creator'],
                    'player_skip': ['webpage', 'js', 'configs'],
                    'hls_use_mpd': True,
                }
            },
            'compat_opts': ['no-youtube-po-token'],
            'check_formats': 'selected',
            'geo_bypass': True,
        }
    
    async def download(self, url: str, options: Dict[str, Any]) -> Optional[str]:
        # yt-dlp를 사용한 다운로드 구현
        # Playwright 옵션 포함 가능
        pass
```

#### 2.4 Playwright 엔진 구현
```python
class PlaywrightStrategy(DownloadEngine):
    def __init__(self, config):
        self.config = config
        self.playwright = None
        self.browser = None
        self.context = None
    
    async def download(self, url: str, options: Dict[str, Any]) -> Optional[str]:
        # Playwright를 사용한 브라우저 자동화
        # JavaScript challenge 해결
        # PO 토큰 추출
        # 다운로드 링크 확보 및 파일 다운로드
        pass
    
    def setup_browser_context(self):
        # 브라우저 지문 우회 설정
        # 헤더 및 속성 조정
        pass
```

### 3. 회피 전략 구현

#### 3.1 IP 프록시 회전 시스템
```python
import itertools
import random
from typing import List

class ProxyManager:
    def __init__(self, proxy_list: List[str]):
        self.proxy_list = proxy_list
        self.proxy_cycle = itertools.cycle(proxy_list)
        self.proxy_status = {proxy: 'available' for proxy in proxy_list}
    
    def get_next_proxy(self) -> str:
        # 다음 사용 가능한 프록시 반환
        available_proxies = [p for p, status in self.proxy_status.items() if status == 'available']
        if available_proxies:
            return random.choice(available_proxies)
        return next(self.proxy_cycle)
    
    def mark_proxy_status(self, proxy: str, status: str):
        # 프록시 상태 업데이트 (success, failed, blocked)
        self.proxy_status[proxy] = status
```

#### 3.2 요청 간격 조절 시스템
```python
import time
import random
from datetime import datetime, timedelta

class RequestThrottler:
    def __init__(self, min_delay: float = 15.0, max_delay: float = 30.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = None
        self.request_history = []
    
    def delay_before_request(self):
        """요청 전 지연 적용"""
        if self.last_request_time:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_delay:
                time.sleep(self.min_delay - elapsed)
        
        self.last_request_time = time.time()
    
    def random_delay(self):
        """무작위 지연 적용"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
```

#### 3.3 브라우저 지문 우회
```python
class BrowserFingerprintBypass:
    @staticmethod
    def get_random_browser_config():
        """무작위 브라우저 설정 생성"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        viewport_sizes = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1536, 'height': 864}
        ]
        
        return {
            'user_agent': random.choice(user_agents),
            'viewport': random.choice(viewport_sizes),
            'locale': random.choice(['en-US', 'ko-KR', 'ja-JP']),
            'timezone': random.choice(['Asia/Seoul', 'America/New_York', 'Europe/London'])
        }
```

### 4. 상태 관리 및 모니터링

#### 4.1 다운로드 상태 관리
```python
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

class DownloadStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

@dataclass
class DownloadTask:
    task_id: str
    url: str
    status: DownloadStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    download_path: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    strategy_used: Optional[str] = None
```

#### 4.2 성능 모니터링
```python
class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'total_requests': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'average_time': 0.0,
            'strategy_performance': {}
        }
    
    def record_attempt(self, strategy: str):
        """다운로드 시도 기록"""
        self.metrics['total_requests'] += 1
        if strategy not in self.metrics['strategy_performance']:
            self.metrics['strategy_performance'][strategy] = {
                'attempts': 0,
                'successes': 0,
                'failures': 0,
                'avg_time': 0
            }
        self.metrics['strategy_performance'][strategy]['attempts'] += 1
    
    def record_success(self, strategy: str, time_taken: float):
        """다운로드 성공 기록"""
        self.metrics['successful_downloads'] += 1
        self.metrics['strategy_performance'][strategy]['successes'] += 1
        
        # 평균 시간 업데이트
        perf = self.metrics['strategy_performance'][strategy]
        perf['avg_time'] = (
            (perf['avg_time'] * perf['successes'] + time_taken) / 
            (perf['successes'] + 1)
        )
    
    def record_failure(self, strategy: str):
        """다운로드 실패 기록"""
        self.metrics['failed_downloads'] += 1
        self.metrics['strategy_performance'][strategy]['failures'] += 1
```

### 5. 에러 처리 및 복구

#### 5.1 오류 분류 및 처리
```python
class DownloadError(Exception):
    """다운로드 관련 기본 예외 클래스"""
    pass

class SecurityChallengeError(DownloadError):
    """보안 챌린지 관련 오류 (PO 토큰, JS 등)"""
    pass

class RateLimitError(DownloadError):
    """요청 제한 관련 오류"""
    pass

class NetworkError(DownloadError):
    """네트워크 관련 오류"""
    pass

class ContentUnavailableError(DownloadError):
    """콘텐츠 이용 불가 관련 오류"""
    pass
```

#### 5.2 자동 복구 시스템
```python
import asyncio
from typing import List

class AutoRecoverySystem:
    def __init__(self, strategy_selector, download_engines):
        self.strategy_selector = strategy_selector
        self.download_engines = download_engines
        self.retry_schedule = [5, 10, 30, 60, 120]  # 재시도 간격(초)
    
    async def handle_error(self, url: str, error: Exception, current_strategy: str) -> bool:
        """오류 처리 및 자동 복구"""
        if isinstance(error, SecurityChallengeError):
            # 다른 전략으로 전환
            return await self.switch_strategy_and_retry(url)
        elif isinstance(error, RateLimitError):
            # 대기 후 재시도
            await asyncio.sleep(60)  # 1분 대기
            return await self.retry_with_current_strategy(url, current_strategy)
        elif isinstance(error, NetworkError):
            # 프록시 변경 후 재시도
            return await self.retry_with_different_proxy(url, current_strategy)
        else:
            # 일반 오류 - 다른 전략 시도
            return await self.switch_strategy_and_retry(url)
    
    async def switch_strategy_and_retry(self, url: str) -> bool:
        """전략을 변경하여 재시도"""
        # 현재 실패한 전략 제외
        available_strategies = [s for s in self.download_engines.keys() 
                              if s != 'YTDLPCookieStrategy']
        for strategy_name in available_strategies:
            engine = self.download_engines[strategy_name]
            try:
                result = await engine.download(url, {})
                if result:
                    return True
            except Exception as e:
                continue
        return False
```

### 6. 보안 및 무결성

#### 6.1 쿠키 및 인증 관리
```python
class AuthManager:
    def __init__(self, cookies_file: str):
        self.cookies_file = cookies_file
        self.cookies = self.load_cookies()
    
    def load_cookies(self):
        """쿠키 파일 로드 및 유효성 검사"""
        # 쿠키가 유효한지 확인
        # 만료된 쿠키 재설정 필요 여부 확인
        pass
    
    def refresh_cookies(self):
        """쿠키 갱신"""
        # Playwright를 사용하여 새 쿠키 확보
        pass
    
    def validate_cookies(self) -> bool:
        """쿠키 유효성 검사"""
        # 실제 요청을 통해 쿠키 유효성 확인
        pass
```

#### 6.2 데이터 무결성 확인
```python
import hashlib
import os

class IntegrityChecker:
    @staticmethod
    def calculate_file_hash(filepath: str) -> str:
        """파일 해시 계산"""
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    @staticmethod
    def verify_download_integrity(filepath: str, expected_size: int = None) -> bool:
        """다운로드된 파일 무결성 확인"""
        if expected_size:
            actual_size = os.path.getsize(filepath)
            if actual_size != expected_size:
                return False
        return True
```

이 아키텍처는 YouTube의 2025년 12월 기준 강력한 보안 정책을 고려한 설계로, 다중 레이어 전략을 통해 높은 다운로드 성공률을 달성하도록 구성되어 있습니다.