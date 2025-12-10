# HCL Poker Clips 자동 다운로드 앱 - QWEN Context

## 프로젝트 개요

HCL Poker Clips 자동 다운로드 앱은 YouTube 채널 "https://www.youtube.com/@HCLPokerClips/videos"의 동영상을 매일 자동으로 다운로드 받는 웹 기반 애플리케이션입니다. YouTube의 정책 변경에 대비한 회피 전략을 포함하여 지속적으로 동영상을 다운로드 받을 수 있도록 설계되었습니다.

## 주요 목적

- HCL Poker Clips 채널의 동영상을 자동으로 다운로드
- YouTube 정책 변경에 따른 차단을 우회하는 회피 전략 구현
- 웹 기반 인터페이스 제공
- 일일 자동 실행 및 다운로드 상태 모니터링

## 아키텍처 개요

### 블록화 + 에이전트 시스템 (Block Agent System)

이 프로젝트는 블록화와 에이전트 시스템을 기반으로 한 아키텍처를 채택하고 있습니다. 이 구조는 AI 컨텍스트 최적화를 위해 설계되었으며, 다음과 같은 주요 특징을 가집니다:

#### 1. 블록화 (Block System)
- **단일 책임 원칙**: 하나의 블록은 하나의 관심사만 담당
- **수직 분할 (Vertical Slicing)**: 기능 단위로 관련된 모든 코드를 하나의 블록에 포함
- **자체 완결성 (Self-Contained)**: 블록은 자체적으로 완결적인 기능을 제공

#### 2. 에이전트 시스템 (Agent System)
- **계층적 구조**: 오케스트레이터 → 도메인 에이전트 → 블록 에이전트
- **역할 분리**: 각 에이전트는 특정 도메인 또는 블록을 전담
- **지능형 조정**: 오케스트레이터가 전체 워크플로우를 조정

#### 3. 도메인 구조
- **Auth Domain**: 인증/인가 관련 기능
- **Content Domain**: 콘텐츠 조회 및 캐시 관리
- **Stream Domain**: 스트리밍 관련 기능
- **Search Domain**: 검색 기능

### 시스템 구성도
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   사용자 UI     │◄──►│   웹 서버        │◄──►│   작업 스케줄러     │
│ (웹 브라우저)   │    │ (API 서버)       │    │ (Cron/Scheduler)    │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐    ┌─────────────────────┐
                    │   다운로드 큐    │◄──►│   다운로드 엔진     │
                    │   (Redis/RabbitMQ)│    │   (Headless Chrome) │
                    └──────────────────┘    └─────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   데이터베이스   │
                    │   (PostgreSQL)   │
                    └──────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   파일 저장소    │
                    │   (Local/Cloud)  │
                    └──────────────────┘
```

## 기술 스택

- **프론트엔드**: React.js 또는 Vue.js
- **백엔드**: Node.js/Express.js 또는 Python/FastAPI
- **데이터베이스**: PostgreSQL 또는 MongoDB
- **다운로드 엔진**: Headless Chrome 기반
- **프록시 관리**: 다중 프록시 회전 시스템
- **큐 관리**: Redis, RabbitMQ 또는 Bull Queue
- **캐싱**: Redis
- **스트리밍**: FFmpeg, HLS

## 핵심 기능

### 1. 자동 일일 다운로드
- HCL Poker Clips 채널의 새로운 동영상 자동 검색
- 설정 가능한 스케줄에 따른 다운로드
- 화질 선택 옵션 (가장 높은 화질, 1080p, 720p 등)
- 중복 다운로드 방지 기능

### 2. 내결함성 다운로드 시스템
- 차단 상황 시 대체 방법 제공
- 지수 백오프 방식의 재시도 메커니즘
- 중단된 다운로드의 재개 기능
- 자동 오류 감지 및 복구

### 3. 회피 전략
- **시그니처 난독화 대응**: 실시간 시그니처 추출 알고리즘 업데이트, 다중 추출 방법 구현
- **속도 제한 회피**: 지능형 요청 조절 및 무작위 지연, 다중 프록시 회전
- **CAPTCHA 처리**: CAPTCHA 해결 서비스 통합, 챔린지 해결을 위한 브라우저 자동화
- **적응형 기법**: 차단 지표의 지속적 모니터링, 대체 방법 자동 전환

## 파일 구조

```
C:\claude\HCL_Poker_Clips\
├── Architecture_Design.md       # 시스템 아키텍처 설계서
├── Evasion_Strategy.md          # 회피 전략 설계서
├── FINAL_REPORT.md
├── get_channel_info.py
├── LICENSE
├── MANUAL_URL_GUIDE.md
├── Product_Requirements_Document.md # 제품 요구사항 문서
├── PROJECT_SUMMARY.md
├── QWEN.md
├── README.md                   # 프로젝트 개요
├── run_downloader.py
├── test_downloader.py
├── .git\...
├── docs/
│   └── block_agent_system.md   # 블록-에이전트 시스템 아키텍처 문서
├── downloads/
└── src/
    ├── config/
    │   └── config.py           # 설정 관리 모듈
    ├── download/
    │   └── main.py             # 메인 다운로드 로직
    ├── gui/
    │   ├── gui_app.py          # Tkinter GUI 애플리케이션
    │   └── web_server.py       # Flask 웹 서버
    └── utils/
        └── youtube_utils.py    # YouTube API 및 유틸리티 함수
```

## 주요 모듈 설명

### 1. src/config/config.py
- 애플리케이션의 모든 설정 값을 관리
- 환경변수와 config.ini 파일을 기반으로 설정을 로드
- yt-dlp 다운로드 옵션 및 회피 전략 설정 포함

### 2. src/download/main.py
- 주요 다운로드 로직을 포함하는 메인 모듈
- HCLPokerClipsDownloader 클래스는 채널에서 동영상 목록을 가져오고 다운로드를 수행
- 재시도 로직 및 회피 전략 적용 포함

### 3. src/utils/youtube_utils.py
- YouTube 채널에서 동영상 URL을 추출하는 유틸리티 함수들
- RSS 피드와 yt-dlp를 사용하여 동영상 목록을 가져오는 다양한 방법 구현
- 동영상 정보 추출 및 유효성 검사 기능 포함

### 4. src/gui/web_server.py
- Flask 기반의 웹 인터페이스 제공
- 사용자가 UI를 통해 다운로드 작업을 시작할 수 있음

### 5. src/gui/gui_app.py
- Tkinter 기반의 데스크톱 GUI 애플리케이션
- URL 입력 및 다운로드 진행 상태 표시

## 주요 설정 옵션

| 설정 | 설명 | 기본값 |
|------|------|--------|
| DOWNLOAD_DIR | 다운로드 파일 저장 위치 | downloads |
| MAX_RETRIES | 다운로드 실패 시 재시도 횟수 | 3 |
| YTDLP_FORMAT | 다운로드 화질 설정 | best[height<=1080] |
| REQUEST_DELAY_MIN | 요청 최소 대기 시간 (초) | 1.0 |
| REQUEST_DELAY_MAX | 요청 최대 대기 시간 (초) | 3.0 |
| MAX_DELAY_SECONDS | 재시도 시 최대 대기 시간 (초) | 15.0 |
| LOG_LEVEL | 로그 레벨 | INFO |

## 실행 방법

### 1. 의존성 설치
```bash
pip install -r requirements.txt
```

### 2. 애플리케이션 실행
```bash
python run_downloader.py
```

### 3. 웹 인터페이스 실행
```bash
python -m src.gui.web_server
```

### 4. GUI 애플리케이션 실행
```bash
python -m src.gui.gui_app
```

## 회피 전략 상세

### 요청 간격 조절
- 다운로드 요청 사이에 무작위 지연을 적용
- 설정 파일의 REQUEST_DELAY_MIN과 REQUEST_DELAY_MAX 값에 따라 지연

### 사용자 에이전트 무작위 변경
- fake-useragent 라이브러리를 사용하여 요청 시 랜덤한 사용자 에이전트 적용

### 쿠키 기반 접근
- YouTube 로그인 상태를 유지하기 위한 쿠키 파일 사용 가능
- cookies.txt 파일을 프로젝트 루트에 배치하면 자동으로 사용

### 수동 URL 추가
- 자동 채널 분석이 실패한 경우, manual_urls.txt 파일을 통해 수동으로 URL 지정 가능

## 개발 규칙

### 블록 규칙
- 블록은 15~30개 파일 / 30k~50k 토큰 크기를 유지
- 단일 책임 원칙 준수
- 자체 완결성 보장 (Self-Contained)
- 외부 파일 직접 수정 금지

### 에이전트 규칙
- 도메인 에이전트는 해당 도메인 블록만 관리
- 블록 에이전트는 단일 블록만 관리
- 오케스트레이터는 전역 조정 및 에러 처리 담당

### 코드 스타일
- 타입스크립트 기반
- Zod 스키마를 사용한 입력 검증
- 오류 처리 및 회로 차단기 적용

## 빌드 및 실행 (예정)

구현이 완료된 후에는 다음과 같은 명령어를 사용하여 빌드 및 실행할 수 있습니다:

- 개발 서버 시작: `npm run dev`
- 빌드: `npm run build`
- 테스트 실행: `npm test`
- 프로덕션 서버 시작: `npm start`

(이 부분은 패키지 파일이 현재 존재하지 않으므로 추후 구현 예정)

## 주요 도전 과제

1. **YouTube 정책 회피**: 자동화 탐지 및 차단 회피
2. **법적 문제**: 저작권 및 이용약관 관련 문제 해결
3. **확장성**: 다수 사용자 및 대량 콘텐츠 처리
4. **안정성**: 지속적인 서비스 제공을 위한 내결함성

## 보안 고려사항

- JWT 기반 인증 시스템
- 민감한 데이터 암호화 (AES-256)
- API 속도 제한 (Rate Limiting)
- CORS 설정 관리
- 네트워크 통신은 HTTPS/TLS 암호화 사용

## 테스트

- 테스트 스크립트: `python test_downloader.py`
- YouTube 유틸리티, 설정 모듈, 다운로더 클래스의 기본 기능 테스트