# 프록시 회전 및 요청 조절 시스템 설계
## HCL Poker Clips 자동 다운로드 앱 (2025년 12월 기준)

### 1. 시스템 개요

YouTube의 IP 기반 차단 및 속도 제한을 우회하기 위해 프록시 회전과 요청 조절 시스템이 필요합니다. 이 시스템은 다양한 IP 주소를 통해 요청을 분산시키고, 요청 빈도를 조절하여 차단을 방지합니다.

### 2. 프록시 관리 시스템

#### 2.1 프록시 관리자 클래스
```python
import random
import asyncio
import aiohttp
import time
from typing import List, Dict, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

class ProxyStatus(Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    FAILED = "failed"
    BLOCKED = "blocked"
    SLOW = "slow"

@dataclass
class ProxyInfo:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    country: Optional[str] = None
    type: str = "http"  # http, https, socks4, socks5
    status: ProxyStatus = ProxyStatus.AVAILABLE
    last_use_time: Optional[datetime] = None
    last_test_time: Optional[datetime] = None
    success_rate: float = 1.0
    response_time: float = 0.0
    failure_count: int = 0
    success_count: int = 0

class ProxyManager:
    def __init__(self, proxy_list: List[Dict[str, str]], config=None):
        self.proxies: List[ProxyInfo] = self._parse_proxy_list(proxy_list)
        self.config = config or self._get_default_config()
        self._lock = asyncio.Lock()
        self._busy_proxies: Dict[str, datetime] = {}
        self._proxy_usage_stats: Dict[str, Dict] = {}
    
    def _get_default_config(self):
        return {
            'min_success_rate': 0.7,  # 최소 성공률
            'max_response_time': 5.0,  # 최대 응답 시간 (초)
            'max_consecutive_failures': 3,  # 최대 연속 실패 횟수
            'proxy_test_interval': 300,  # 프록시 테스트 간격 (초)
            'proxy_cooldown_time': 600,  # 프록시 쿨다운 시간 (초)
            'request_delay_range': (15.0, 30.0)  # 요청 지연 시간 범위
        }
    
    def _parse_proxy_list(self, proxy_list: List[Dict[str, str]]) -> List[ProxyInfo]:
        """프록시 목록 파싱"""
        proxies = []
        for proxy_data in proxy_list:
            proxy_info = ProxyInfo(
                host=proxy_data['host'],
                port=proxy_data['port'],
                username=proxy_data.get('username'),
                password=proxy_data.get('password'),
                country=proxy_data.get('country', 'Unknown'),
                type=proxy_data.get('type', 'http')
            )
            proxies.append(proxy_info)
        return proxies
    
    async def get_available_proxy(self) -> Optional[ProxyInfo]:
        """사용 가능한 프록시 가져오기"""
        async with self._lock:
            # 현재 사용 중이거나 쿨다운 중인 프록시 필터링
            now = datetime.now()
            available_proxies = []
            
            for proxy in self.proxies:
                # 프록시가 사용 중인지 확인
                busy_until = self._busy_proxies.get(f"{proxy.host}:{proxy.port}")
                if busy_until and busy_until > now:
                    continue
                
                # 상태에 따른 필터링
                if proxy.status in [ProxyStatus.FAILED, ProxyStatus.BLOCKED]:
                    # 쿨다운 시간 경과 확인
                    if proxy.last_test_time:
                        cooldown_end = proxy.last_test_time + timedelta(
                            seconds=self.config['proxy_cooldown_time']
                        )
                        if now < cooldown_end:
                            continue
                
                # 성능 기반 필터링
                if (proxy.success_rate < self.config['min_success_rate'] or 
                    (proxy.response_time > 0 and 
                     proxy.response_time > self.config['max_response_time'])):
                    continue
                
                available_proxies.append(proxy)
            
            if not available_proxies:
                return None
            
            # 성공률 높은 프록시 우선, 무작위성도 고려
            available_proxies.sort(key=lambda x: x.success_rate, reverse=True)
            
            # 상위 30%만 무작위 선택 (성능과 무작위성의 균형)
            top_proxies = available_proxies[:max(1, len(available_proxies) // 3)]
            selected_proxy = random.choice(top_proxies)
            
            # 프록시를 사용 중으로 표시
            self._mark_proxy_busy(selected_proxy)
            
            return selected_proxy
    
    def _mark_proxy_busy(self, proxy: ProxyInfo):
        """프록시를 사용 중으로 표시"""
        proxy_key = f"{proxy.host}:{proxy.port}"
        busy_duration = timedelta(seconds=30)  # 30초간 사용 중으로 표시
        self._busy_proxies[proxy_key] = datetime.now() + busy_duration
        proxy.last_use_time = datetime.now()
    
    def mark_proxy_success(self, proxy: ProxyInfo, response_time: float):
        """프록시 성공 표시"""
        async with self._lock:
            proxy.success_count += 1
            proxy.success_rate = proxy.success_count / (proxy.success_count + proxy.failure_count)
            
            # 응답 시간 업데이트 (이동 평균)
            alpha = 0.3  # 이동 평균 계수
            proxy.response_time = alpha * response_time + (1 - alpha) * proxy.response_time
            
            proxy.status = ProxyStatus.AVAILABLE
    
    def mark_proxy_failure(self, proxy: ProxyInfo, failure_type: str = "general"):
        """프록시 실패 표시"""
        async with self._lock:
            proxy.failure_count += 1
            proxy.success_rate = proxy.success_count / max(1, (proxy.success_count + proxy.failure_count))
            
            # 연속 실패 횟수 확인
            if proxy.failure_count >= self.config['max_consecutive_failures']:
                if failure_type == "blocked":
                    proxy.status = ProxyStatus.BLOCKED
                else:
                    proxy.status = ProxyStatus.FAILED
                proxy.last_test_time = datetime.now()
            
            # 상태에 따라 프록시 풀에서 제외
    
    async def test_proxy(self, proxy: ProxyInfo) -> bool:
        """프록시 테스트"""
        try:
            proxy_url = self._build_proxy_url(proxy)
            
            start_time = time.time()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    'https://httpbin.org/ip', 
                    proxy=proxy_url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        # 성공률과 응답 시간 업데이트
                        self.mark_proxy_success(proxy, response_time)
                        return True
                    else:
                        self.mark_proxy_failure(proxy)
                        return False
        except Exception as e:
            print(f"프록시 테스트 실패 {proxy.host}:{proxy.port} - {str(e)}")
            self.mark_proxy_failure(proxy)
            return False
    
    def _build_proxy_url(self, proxy: ProxyInfo) -> str:
        """프록시 URL 생성"""
        if proxy.type.lower() in ['socks4', 'socks5']:
            protocol = f"socks5://{proxy.host}:{proxy.port}"
        else:
            protocol = f"http://{proxy.host}:{proxy.port}"
        
        if proxy.username and proxy.password:
            # 인증 정보 포함
            auth = f"{proxy.username}:{proxy.password}"
            protocol = protocol.replace(f"{proxy.host}:{proxy.port}", f"{auth}@{proxy.host}:{proxy.port}")
        
        return protocol
    
    async def validate_all_proxies(self):
        """모든 프록시 검증 (백그라운드 작업)"""
        for proxy in self.proxies:
            await self.test_proxy(proxy)
```

### 3. 요청 조절 시스템 (Request Throttling)

#### 3.1 요청 조절 관리자
```python
import random
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio

class RequestThrottler:
    def __init__(self, config=None):
        self.config = config or self._get_default_config()
        self._request_history = {}  # URL별 요청 기록
        self._host_limits = {}  # 호스트별 요청 제한
        self._global_limits = {}  # 전역 요청 제한
        self._lock = asyncio.Lock()
    
    def _get_default_config(self):
        return {
            'min_request_interval': 15.0,  # 최소 요청 간격 (초)
            'max_request_interval': 30.0,  # 최대 요청 간격 (초)
            'requests_per_minute': 2,  # 분당 최대 요청 수
            'requests_per_hour': 30,   # 시간당 최대 요청 수
            'concurrent_requests_per_host': 1,  # 호스트당 동시 요청 수
        }
    
    async def can_make_request(self, url: str) -> Tuple[bool, Optional[float]]:
        """
        요청 가능 여부 확인 및 필요 지연 시간 반환
        :return: (요청 가능 여부, 필요 지연 시간(초))
        """
        async with self._lock:
            host = self._extract_host(url)
            
            now = datetime.now()
            
            # 호스트별 제한 확인
            host_requests = self._host_limits.get(host, [])
            recent_host_requests = [
                req_time for req_time in host_requests 
                if now - req_time < timedelta(minutes=1)
            ]
            
            if len(recent_host_requests) >= self.config['requests_per_minute']:
                # 제한 초과 시, 다음 요청 가능 시간 계산
                earliest_next = recent_host_requests[0] + timedelta(minutes=1)
                delay = (earliest_next - now).total_seconds()
                return False, max(delay, 1.0)
            
            # 전역 제한 확인
            global_requests = self._global_limits.get('all', [])
            recent_global_requests = [
                req_time for req_time in global_requests 
                if now - req_time < timedelta(hours=1)
            ]
            
            if len(recent_global_requests) >= self.config['requests_per_hour']:
                delay = 3600  # 1시간 대기
                return False, delay
            
            return True, 0.0
    
    async def register_request(self, url: str):
        """요청 등록"""
        async with self._lock:
            host = self._extract_host(url)
            now = datetime.now()
            
            # 호스트별 요청 기록
            if host not in self._host_limits:
                self._host_limits[host] = []
            self._host_limits[host].append(now)
            
            # 전역 요청 기록
            if 'all' not in self._global_limits:
                self._global_limits['all'] = []
            self._global_limits['all'].append(now)
    
    def _extract_host(self, url: str) -> str:
        """URL에서 호스트 추출"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"
    
    async def get_delay_time(self) -> float:
        """요청 전 대기 시간 계산"""
        min_delay = self.config['min_request_interval']
        max_delay = self.config['max_request_interval']
        
        # 무작위 지연 시간 (Jitter 포함)
        delay = random.uniform(min_delay, max_delay)
        
        # 부하 분산을 위한 추가 지연 (선택적)
        if random.random() > 0.7:  # 30% 확률로 추가 지연
            extra_delay = random.uniform(1.0, 5.0)
            delay += extra_delay
        
        return delay
```

### 4. IP 회피 전략

#### 4.1 IP 감지 및 우회
```python
import re
import asyncio
from typing import Dict, List

class IPBypassStrategy:
    def __init__(self, proxy_manager: ProxyManager):
        self.proxy_manager = proxy_manager
        self._detected_patterns = []
        self._ip_cooldown = {}
    
    async def should_use_proxy(self, response_text: str, status_code: int) -> bool:
        """프록시 사용 여부 판단"""
        # 차단 감지 패턴 확인
        blocking_patterns = [
            r'access denied',
            r'blocked',
            r'rate limit',
            r'too many requests',
            r'403 forbidden',
            r'429',
            r'cloudflare',
            r'bot detection',
            r'checking your browser'
        ]
        
        text_lower = response_text.lower()
        for pattern in blocking_patterns:
            if re.search(pattern, text_lower) or status_code in [403, 429, 503]:
                return True
        
        return False
    
    async def get_ip_specific_headers(self, proxy: ProxyInfo) -> Dict[str, str]:
        """IP 기반 헤더 조정"""
        # 프록시의 위치 정보에 따라 다른 헤더 설정
        country_headers = {
            'US': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.google.com/',
                'X-Forwarded-For': await self._generate_random_ip_for_country(proxy.country)
            },
            'KR': {
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.google.co.kr/',
                'X-Forwarded-For': await self._generate_random_ip_for_country(proxy.country)
            },
            'JP': {
                'Accept-Language': 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://www.google.co.jp/',
                'X-Forwarded-For': await self._generate_random_ip_for_country(proxy.country)
            }
        }
        
        headers = country_headers.get(proxy.country, {})
        
        # 기본 헤더 추가
        headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        })
        
        return headers
    
    async def _generate_random_ip_for_country(self, country: str) -> str:
        """지정된 국가의 IP 대역에서 무작위 IP 생성"""
        # 실제 구현에서는 국가별 IP 대역 데이터베이스를 사용해야 함
        # 여기서는 예시로 간단한 구현
        country_ip_ranges = {
            'US': ['104.154', '34.92', '34.104'],
            'KR': ['147.46', '211.110', '125.140'],
            'JP': ['157.119', '219.122', '124.152']
        }
        
        ip_range = random.choice(country_ip_ranges.get(country, ['192.168']))
        last_octets = [random.randint(1, 254) for _ in range(2)]
        return f"{ip_range}.{last_octets[0]}.{last_octets[1]}"
```

### 5. 지능형 요청 분산 시스템

#### 5.1 요청 분산 알고리즘
```python
from collections import defaultdict
import statistics

class IntelligentRequestDistributor:
    def __init__(self, proxy_manager: ProxyManager, throttler: RequestThrottler):
        self.proxy_manager = proxy_manager
        self.throttler = throttler
        self._performance_history = defaultdict(list)  # 프록시 성능 기록
        self._load_balancer = LoadBalancer()
    
    async def distribute_request(self, url: str) -> Optional[Tuple[ProxyInfo, Dict[str, str], float]]:
        """
        요청을 적절한 프록시에 분산
        :return: (프록시 정보, 요청 헤더, 대기 시간)
        """
        # 사용 가능한 프록시 가져오기
        proxy = await self.proxy_manager.get_available_proxy()
        if not proxy:
            print("사용 가능한 프록시가 없습니다")
            return None
        
        # 요청 허용 여부 확인
        can_request, delay = await self.throttler.can_make_request(url)
        if not can_request:
            print(f"요청 제한: {delay}초 대기 필요")
            return None
        
        # IP별 헤더 가져오기
        headers = await self._get_optimized_headers_for_proxy(proxy, url)
        
        # 요청 등록
        await self.throttler.register_request(url)
        
        return proxy, headers, delay
    
    async def _get_optimized_headers_for_proxy(self, proxy: ProxyInfo, url: str) -> Dict[str, str]:
        """프록시에 최적화된 요청 헤더 생성"""
        # 국가별 헤더 설정
        ip_bypass = IPBypassStrategy(self.proxy_manager)
        headers = await ip_bypass.get_ip_specific_headers(proxy)
        
        # 사용자 에이전트 무작위화
        user_agents = self._get_random_user_agents_for_proxies(proxy.country)
        headers['User-Agent'] = random.choice(user_agents)
        
        # 다른 헤더도 무작위화 또는 최적화
        headers['Accept'] = random.choice([
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'application/json, text/plain, */*',
            'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        ])
        
        return headers
    
    def _get_random_user_agents_for_proxies(self, country: str) -> List[str]:
        """국가에 맞는 무작위 사용자 에이전트 목록"""
        # 국가별로 흔히 사용되는 브라우저/OS 조합
        if country == 'KR':
            return [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        elif country == 'US':
            return [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0'
            ]
        else:
            return [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]

class LoadBalancer:
    """로드 밸런서 클래스"""
    def __init__(self):
        self._request_counts = defaultdict(int)
        self._last_used_time = defaultdict(datetime.now)
    
    def select_proxy_by_load(self, available_proxies: List[ProxyInfo]) -> ProxyInfo:
        """로드 밸런싱 알고리즘으로 프록시 선택"""
        if not available_proxies:
            return None
        
        # 가장 적게 사용된 프록시 선택 (라운드 로빈)
        min_requests = min(p.success_count + p.failure_count for p in available_proxies)
        least_used = [p for p in available_proxies if p.success_count + p.failure_count == min_requests]
        
        # 성능이 비슷한 경우 무작위 선택
        return random.choice(least_used)
```

### 6. 통합 관리자

#### 6.1 프록시 및 요청 통합 관리
```python
class ProxyRequestManager:
    def __init__(self, proxy_list: List[Dict[str, str]]):
        self.proxy_manager = ProxyManager(proxy_list)
        self.throttler = RequestThrottler()
        self.ip_bypass = IPBypassStrategy(self.proxy_manager)
        self.distributor = IntelligentRequestDistributor(
            self.proxy_manager, 
            self.throttler
        )
        self._session_cache = {}
    
    async def get_request_config(self, url: str) -> Optional[Dict]:
        """
        요청 설정 가져오기
        :return: {'proxy': ProxyInfo, 'headers': dict, 'delay': float} 또는 None
        """
        result = await self.distributor.distribute_request(url)
        if result:
            proxy, headers, delay = result
            return {
                'proxy': proxy,
                'headers': headers,
                'delay': delay
            }
        return None
    
    async def make_request_with_proxy(self, url: str, method: str = 'GET', **kwargs):
        """프록시를 사용한 요청 실행"""
        config = await self.get_request_config(url)
        if not config:
            raise Exception("요청 설정을 가져올 수 없습니다")
        
        proxy_info = config['proxy']
        headers = config['headers']
        delay = config['delay']
        
        # 지연 적용
        if delay > 0:
            await asyncio.sleep(delay)
        
        # 프록시 URL 생성
        proxy_url = self.proxy_manager._build_proxy_url(proxy_info)
        
        # 요청 실행
        try:
            async with aiohttp.ClientSession() as session:
                # kwargs에 헤더, 프록시 등 추가 설정 반영
                request_kwargs = {
                    'method': method,
                    'url': url,
                    'proxy': proxy_url,
                    'headers': headers,
                    'timeout': aiohttp.ClientTimeout(total=30)
                }
                request_kwargs.update(kwargs)
                
                async with session.request(**request_kwargs) as response:
                    response_data = await response.text()
                    
                    # 응답 분석을 통한 프록시 성능 평가
                    is_blocked = await self.ip_bypass.should_use_proxy(response_data, response.status)
                    
                    if is_blocked:
                        self.proxy_manager.mark_proxy_failure(proxy_info, "blocked")
                        print(f"프록시 차단 감지: {proxy_info.host}:{proxy_info.port}")
                    else:
                        self.proxy_manager.mark_proxy_success(
                            proxy_info, 
                            response.headers.get('X-Response-Time', 1.0)
                        )
                    
                    return {
                        'status': response.status,
                        'headers': dict(response.headers),
                        'content': response_data,
                        'proxy_used': f"{proxy_info.host}:{proxy_info.port}"
                    }
        except Exception as e:
            self.proxy_manager.mark_proxy_failure(proxy_info, "connection_error")
            raise e
    
    async def start_background_tasks(self):
        """백그라운드 작업 시작"""
        # 프록시 검증 작업 시작
        asyncio.create_task(self._periodic_proxy_validation())
    
    async def _periodic_proxy_validation(self):
        """정기적으로 프록시 검증"""
        while True:
            try:
                await self.proxy_manager.validate_all_proxies()
                await asyncio.sleep(300)  # 5분마다 검증
            except Exception as e:
                print(f"프록시 검증 중 오류 발생: {e}")
                await asyncio.sleep(60)  # 오류 발생 시 1분 후 재시도
```

### 7. 설정 및 모니터링

#### 7.1 시스템 설정
```python
class ProxyThrottleConfig:
    """프록시 및 요청 조절 시스템 설정"""
    
    # 기본 설정
    DEFAULT_CONFIG = {
        # 프록시 설정
        'proxy_min_success_rate': 0.7,
        'proxy_max_response_time': 5.0,
        'proxy_max_consecutive_failures': 3,
        'proxy_test_interval': 300,
        'proxy_cooldown_time': 600,
        
        # 요청 조절 설정
        'min_request_interval': 15.0,
        'max_request_interval': 30.0,
        'requests_per_minute': 2,
        'requests_per_hour': 30,
        'max_concurrent_requests': 5,
        
        # 성능 모니터링 설정
        'monitoring_interval': 60,
        'log_level': 'INFO'
    }
    
    @classmethod
    def load_from_file(cls, config_file: str) -> Dict:
        """설정 파일에서 로드"""
        # 실제 구현에서는 JSON 또는 YAML 파일에서 설정 로드
        return cls.DEFAULT_CONFIG
    
    @classmethod
    def validate_config(cls, config: Dict) -> bool:
        """설정 유효성 검사"""
        required_fields = [
            'min_request_interval', 'max_request_interval',
            'requests_per_minute', 'proxy_min_success_rate'
        ]
        
        for field in required_fields:
            if field not in config:
                return False
        
        # 값 범위 검사
        if config['min_request_interval'] <= 0 or config['max_request_interval'] <= 0:
            return False
        if config['requests_per_minute'] <= 0 or config['requests_per_hour'] <= 0:
            return False
        
        return True
```

이 설계는 YouTube의 2025년 12월 기준 강력한 IP 기반 차단 정책을 우회하기 위해 다중 레이어 접근 방식을 사용하여, 프록시 회전과 요청 조절을 효과적으로 통합한 시스템입니다.