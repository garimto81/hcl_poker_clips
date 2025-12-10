# YouTube 동영상 다운로드 폴백(Fallback) 메커니즘 설계
## HCL Poker Clips 자동 다운로드 앱 (2025년 12월 기준)

### 1. 폴백 시스템 개요

YouTube의 보안 정책이 강화됨에 따라, 첫 번째 다운로드 시도가 실패할 확률이 높아졌습니다. 이를 대비하여 다중 레이어 폴백 시스템을 설계하여, 주요 다운로드 방법이 실패할 경우 대체 전략을 자동으로 실행합니다.

### 2. 폴백 전략 레이어

#### 2.1 1차 폴백: 파라미터 및 설정 변경
- **쿠키 업데이트**: 쿠키가 만료되었을 수 있으므로 갱신
- **헤더 변경**: User-Agent, Referer, Accept-Language 등 변경
- **요청 지연 증가**: 기존보다 더 긴 대기 시간 적용
- **플레이어 클라이언트 변경**: web → android → web_creator 등 순환

#### 2.2 2차 폴백: 대체 다운로드 엔진
- **Playwright 엔진으로 전환**: 브라우저 자동화를 통한 JS challenge 해결
- **API 기반 엔진으로 전환**: 비공식 API를 통한 정보 추출
- **HTTP 요청 엔진으로 전환**: 직접 세그먼트 요청

#### 2.3 3차 폴백: 네트워크 및 환경 변경
- **프록시 서버 변경**: 다른 IP 주소를 통한 요청
- **DNS 변경**: 다른 DNS 서버를 통한 요청
- **지리적 위치 우회**: VPN 또는 지리적으로 분산된 프록시 사용

#### 2.4 4차 폴백: 시간 기반 재시도
- **지수 백오프 방식**: 5초 → 15초 → 30초 → 1분 → 2분 ...
- **시간대 분산**: 특정 시간대에는 차단이 덜 한 경우를 대비
- **요일 기반 전략**: 주말/평일에 따라 다른 전략 적용

### 3. 폴백 트리거 조건

#### 3.1 오류 기반 트리거
- **HTTP 상태 코드**: 429(Rate Limit), 403(Forbidden), 400(Bad Request)
- ** yt-dlp 에러 타입**: 
  - `ExtractorError`: Extractor 관련 오류
  - `DownloadError`: 다운로드 실패
  - `PostProcessingError`: 후처리 실패
- **보안 챌린지 감지**: PO 토큰 오류, JS challenge 실패

#### 3.2 성능 기반 트리거
- **다운로드 속도**: 1KB/s 이하 지속 시
- **연결 실패율**: 3회 연속 연결 실패 시
- **응답 시간**: 30초 이상 응답 없을 시

#### 3.3 정책 변경 감지
- **응답 구조 변경**: 예상과 다른 응답 구조 감지 시
- **필수 파라미터 누락**: signature, url 등 필수 파라미터가 누락된 경우
- **API 엔드포인트 변경**: 기존 엔드포인트가 더 이상 작동하지 않는 경우

### 4. 폴백 전략 구현

#### 4.1 폴백 관리자 클래스
```python
import asyncio
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

class FallbackStrategy(Enum):
    PARAMETER_CHANGE = "parameter_change"
    ENGINE_SWITCH = "engine_switch"
    NETWORK_CHANGE = "network_change"
    TIME_DELAY = "time_delay"

class FallbackManager:
    def __init__(self, config):
        self.config = config
        self.fallback_history = {}
        self.fallback_sequence = [
            self._parameter_change_fallback,
            self._engine_switch_fallback,
            self._network_change_fallback,
            self._time_delay_fallback
        ]
        self.max_retries_per_strategy = 3
        self.current_strategy_index = 0
    
    async def handle_download_failure(self, url: str, error: Exception, context: Dict[str, Any]) -> bool:
        """
        다운로드 실패 시 폴백 전략 실행
        :param url: 대상 URL
        :param error: 발생한 오류
        :param context: 현재 다운로드 컨텍스트
        :return: 성공 여부
        """
        error_type = type(error).__name__
        print(f"다운로드 실패 감지: {error_type}, URL: {url}")
        
        # 오류 타입 기반 초기 전략 선택
        initial_strategy = self._select_initial_fallback_strategy(error)
        
        if initial_strategy:
            result = await initial_strategy(url, context)
            if result:
                return True
        
        # 순차적 폴백 전략 실행
        for idx, fallback_strategy in enumerate(self.fallback_sequence):
            if idx >= self.current_strategy_index:
                self.current_strategy_index = idx
                
                print(f"폴백 전략 실행: {fallback_strategy.__name__}")
                success = await fallback_strategy(url, context)
                
                if success:
                    # 폴백 성공 시 인덱스 초기화
                    self.current_strategy_index = 0
                    return True
        
        # 모든 폴백 전략 실패
        return False
    
    def _select_initial_fallback_strategy(self, error: Exception) -> Optional[Callable]:
        """
        오류 타입 기반 초기 폴백 전략 선택
        """
        error_type = type(error).__name__
        
        if "429" in str(error) or "RateLimit" in error_type:
            # 속도 제한 관련 오류는 시간 지연 전략 우선
            return self._time_delay_fallback
        elif "Forbidden" in str(error) or "403" in str(error):
            # 접근 제한 관련 오류는 네트워크 변경 전략 우선
            return self._network_change_fallback
        elif "PO" in str(error) or "challenge" in str(error).lower():
            # 보안 챌린지 관련 오류는 엔진 변경 전략 우선
            return self._engine_switch_fallback
        else:
            # 그 외 일반 오류는 파라미터 변경 전략 우선
            return self._parameter_change_fallback
    
    async def _parameter_change_fallback(self, url: str, context: Dict[str, Any]) -> bool:
        """
        1차 폴백: 파라미터 및 설정 변경
        """
        print("1차 폴백: 파라미터 및 설정 변경 시도")
        
        # 쿠키 갱신 시도
        if await self._refresh_cookies_if_needed():
            print("쿠키 갱신 성공")
        
        # 헤더 변경
        context['headers'] = self._generate_random_headers()
        
        # 플레이어 클라이언트 변경
        context['player_client'] = self._get_alternative_player_client(context)
        
        # 요청 간격 증가
        context['request_delay'] = context.get('request_delay', 15) + 10
        
        # 재시도
        return await self._retry_download(url, context)
    
    async def _engine_switch_fallback(self, url: str, context: Dict[str, Any]) -> bool:
        """
        2차 폴백: 다운로드 엔진 변경
        """
        print("2차 폴백: 다운로드 엔진 변경 시도")
        
        current_engine = context.get('current_engine', 'yt-dlp')
        available_engines = ['playwright', 'api', 'http']
        
        # 현재 엔진 제외하고 다른 엔진 시도
        alternative_engines = [e for e in available_engines if e != current_engine]
        
        for engine_name in alternative_engines:
            print(f"엔진 변경: {current_engine} -> {engine_name}")
            
            context['current_engine'] = engine_name
            success = await self._try_engine_download(url, engine_name, context)
            
            if success:
                print(f"엔진 변경 성공: {engine_name}")
                return True
        
        return False
    
    async def _network_change_fallback(self, url: str, context: Dict[str, Any]) -> bool:
        """
        3차 폴백: 네트워크 및 환경 변경
        """
        print("3차 폴백: 네트워크 및 환경 변경 시도")
        
        # 프록시 변경
        new_proxy = self._get_new_proxy()
        if new_proxy:
            context['proxy'] = new_proxy
            print(f"프록시 변경: {new_proxy}")
        
        # DNS 변경 (선택적)
        # self._change_dns_server()
        
        # 재시도
        return await self._retry_download(url, context)
    
    async def _time_delay_fallback(self, url: str, context: Dict[str, Any]) -> bool:
        """
        4차 폴백: 시간 기반 재시도
        """
        print("4차 폴백: 시간 기반 재시도")
        
        # 지수 백오프 계산
        retry_count = context.get('retry_count', 0)
        delay = self._calculate_exponential_backoff(retry_count)
        
        print(f"지수 백오프 지연 적용: {delay}초")
        await asyncio.sleep(delay)
        
        # 재시도
        return await self._retry_download(url, context)
    
    def _calculate_exponential_backoff(self, retry_count: int) -> float:
        """
        지수 백오프 시간 계산
        """
        base_delay = self.config.BASE_RETRY_DELAY  # 기본 지연 시간 (예: 5초)
        max_delay = self.config.MAX_RETRY_DELAY    # 최대 지연 시간 (예: 300초)
        
        # 지수 백오프: base_delay * (2 ^ retry_count)
        calculated_delay = min(base_delay * (2 ** retry_count), max_delay)
        
        # 무작위 요소 추가 (Jitter) - 전체 지연 시간의 ±25%
        jitter = calculated_delay * 0.25
        final_delay = max(calculated_delay + random.uniform(-jitter, jitter), 0)
        
        return final_delay
    
    async def _refresh_cookies_if_needed(self) -> bool:
        """
        쿠키 갱신이 필요한 경우 갱신
        """
        # 쿠키 유효성 검사 후 갱신
        # Playwright 등을 사용하여 새 쿠키 확보
        return True  # 갱신 성공 여부 반환
    
    def _generate_random_headers(self) -> Dict[str, str]:
        """
        무작위 요청 헤더 생성
        """
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        accept_languages = ['en-US,en;q=0.9', 'ko-KR,ko;q=0.9', 'ja-JP,ja;q=0.9']
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': random.choice(accept_languages),
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    def _get_alternative_player_client(self, context: Dict[str, Any]) -> str:
        """
        대체 플레이어 클라이언트 가져오기
        """
        current_client = context.get('player_client', 'web')
        alternative_clients = ['android', 'web_creator', 'ios', 'mweb']
        # 현재 클라이언트 제외한 대체 클라이언트 반환
        for client in alternative_clients:
            if client != current_client:
                return client
        return current_client  # 대체 클라이언트가 없을 경우 현재 클라이언트 반환
    
    def _get_new_proxy(self) -> Optional[str]:
        """
        새로운 프록시 서버 가져오기
        """
        # 프록시 관리자에서 새 프록시 가져오기
        # 사용 가능한 프록시 목록에서 가져오기
        return None  # 실제 구현 시 프록시 목록에서 가져옴
    
    async def _retry_download(self, url: str, context: Dict[str, Any]) -> bool:
        """
        주어진 컨텍스트로 다운로드 재시도
        """
        # 실제 다운로드 재시도 로직 구현
        # 엔진을 사용하여 URL 다운로드 시도
        return False  # 실제 구현 시 성공 여부 반환
    
    async def _try_engine_download(self, url: str, engine_name: str, context: Dict[str, Any]) -> bool:
        """
        지정된 엔진으로 다운로드 시도
        """
        # 지정된 엔진으로 다운로드 시도
        return False  # 실제 구현 시 성공 여부 반환
```

### 5. 폴백 상태 추적 및 분석

#### 5.1 폴백 로깅 시스템
```python
import logging
from datetime import datetime
from typing import Dict, Any

class FallbackLogger:
    def __init__(self):
        self.logger = logging.getLogger("fallback")
        self.setup_logger()
        self.fallback_log = []
    
    def setup_logger(self):
        """폴백 로깅 설정"""
        handler = logging.FileHandler('fallback.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_fallback_attempt(self, url: str, strategy: str, context: Dict[str, Any], error: Exception = None):
        """폴백 시도 로그 기록"""
        log_entry = {
            'timestamp': datetime.now(),
            'url': url,
            'strategy': strategy,
            'context': context,
            'error': str(error) if error else None,
            'success': error is None
        }
        
        self.fallback_log.append(log_entry)
        
        self.logger.info(
            f"폴백 시도 - URL: {url}, 전략: {strategy}, "
            f"성공: {error is None}, 오류: {str(error) if error else '없음'}"
        )
    
    def analyze_fallback_effectiveness(self):
        """폴백 전략 효과 분석"""
        total_attempts = len(self.fallback_log)
        successful_attempts = sum(1 for log in self.fallback_log if log['success'])
        
        if total_attempts > 0:
            success_rate = successful_attempts / total_attempts
            return {
                'total_attempts': total_attempts,
                'successful_attempts': successful_attempts,
                'success_rate': success_rate,
                'strategy_effectiveness': self._analyze_by_strategy()
            }
        return {'total_attempts': 0, 'successful_attempts': 0, 'success_rate': 0}
    
    def _analyze_by_strategy(self):
        """전략별 효과 분석"""
        strategy_stats = {}
        for log in self.fallback_log:
            strategy = log['strategy']
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'attempts': 0, 'successes': 0}
            
            strategy_stats[strategy]['attempts'] += 1
            if log['success']:
                strategy_stats[strategy]['successes'] += 1
        
        for strategy, stats in strategy_stats.items():
            stats['success_rate'] = stats['successes'] / stats['attempts']
        
        return strategy_stats
```

### 6. 스마트 폴백 시스템

#### 6.1 머신러닝 기반 폴백 예측
```python
class SmartFallbackPredictor:
    def __init__(self):
        self.historical_data = []
        self.model = None
    
    def record_outcome(self, url: str, initial_strategy: str, fallback_strategy: str, success: bool):
        """결과 기록"""
        record = {
            'url': url,
            'initial_strategy': initial_strategy,
            'fallback_strategy': fallback_strategy,
            'success': success,
            'timestamp': datetime.now()
        }
        self.historical_data.append(record)
    
    def predict_best_fallback(self, error_type: str, previous_strategies: List[str]) -> str:
        """가장 효과적인 폴백 전략 예측"""
        # 간단한 규칙 기반 예측 (ML 모델은 별도 구현 필요)
        if '429' in error_type or 'RateLimit' in error_type:
            return 'time_delay'
        elif '403' in error_type or 'Forbidden' in error_type:
            return 'network_change'
        elif 'PO' in error_type or 'challenge' in error_type.lower():
            return 'engine_switch'
        else:
            return 'parameter_change'
```

### 7. 폴백 제한 및 안전장치

#### 7.1 폴백 제한 시스템
```python
class FallbackLimiter:
    def __init__(self, max_fallbacks_per_url: int = 5, max_fallbacks_per_minute: int = 10):
        self.max_fallbacks_per_url = max_fallbacks_per_url
        self.max_fallbacks_per_minute = max_fallbacks_per_minute
        self.url_fallback_count = {}
        self.minute_fallback_count = 0
        self.last_minute_reset = datetime.now()
    
    def can_attempt_fallback(self, url: str) -> bool:
        """폴백 시도 가능 여부 확인"""
        now = datetime.now()
        
        # 1분 카운트 리셋
        if (now - self.last_minute_reset).seconds >= 60:
            self.minute_fallback_count = 0
            self.last_minute_reset = now
        
        # URL별 카운트 확인
        url_count = self.url_fallback_count.get(url, 0)
        if url_count >= self.max_fallbacks_per_url:
            print(f"URL {url}에 대한 폴백 시도 한도 초과: {url_count}/{self.max_fallbacks_per_url}")
            return False
        
        # 분당 카운트 확인
        if self.minute_fallback_count >= self.max_fallbacks_per_minute:
            print(f"분당 폴백 시도 한도 초과: {self.minute_fallback_count}/{self.max_fallbacks_per_minute}")
            return False
        
        return True
    
    def register_fallback_attempt(self, url: str):
        """폴백 시도 등록"""
        self.url_fallback_count[url] = self.url_fallback_count.get(url, 0) + 1
        self.minute_fallback_count += 1
```

### 8. 사용자 통보 시스템

#### 8.1 폴백 진행 상황 통보
```python
class FallbackNotification:
    def __init__(self):
        self.subscribers = []
    
    def subscribe(self, callback: Callable):
        """구독자 등록"""
        self.subscribers.append(callback)
    
    def notify_fallback_start(self, url: str, initial_strategy: str, error: Exception):
        """폴백 시작 알림"""
        for subscriber in self.subscribers:
            try:
                subscriber('fallback_start', {
                    'url': url,
                    'initial_strategy': initial_strategy,
                    'error': str(error)
                })
            except Exception as e:
                print(f"구독자 알림 오류: {e}")
    
    def notify_fallback_success(self, url: str, final_strategy: str):
        """폴백 성공 알림"""
        for subscriber in self.subscribers:
            try:
                subscriber('fallback_success', {
                    'url': url,
                    'final_strategy': final_strategy
                })
            except Exception as e:
                print(f"구독자 알림 오류: {e}")
    
    def notify_fallback_failure(self, url: str):
        """폴백 실패 알림"""
        for subscriber in self.subscribers:
            try:
                subscriber('fallback_failure', {
                    'url': url
                })
            except Exception as e:
                print(f"구독자 알림 오류: {e}")
```

이 폴백 시스템은 YouTube의 2025년 12월 기준 강력한 보안 정책에 대응하기 위해 설계되었으며, 다중 레이어 접근 방식을 통해 다운로드 성공률을 극대화합니다.