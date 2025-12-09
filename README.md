# HCL Poker Clips 자동 다운로드 앱

이 프로젝트는 https://www.youtube.com/@HCLPokerClips/videos 의 동영상을 매일 자동으로 다운로드 받는 애플리케이션입니다. 유튜브 정책 변경에 대비한 회피 전략을 포함하여 지속적으로 동영상을 다운로드 받을 수 있도록 설계되었습니다.

## 프로젝트 개요

- **목표**: HCL Poker Clips 채널의 동영상을 자동으로 다운로드
- **주기**: 매일 자동 다운로드
- **방식**: Python 기반 커맨드라인 애플리케이션
- **대응 전략**: 유튜브 정책 변경에 대한 회피 전략 포함

## 주요 특징

- 자동 일정 기반 동영상 다운로드
- 유튜브 정책 변경에 대한 회피 전략
- 일일 자동 실행
- 다운로드 상태 모니터링
- 설정 파일을 통한 사용자 정의

## 기술 스택

- 언어: Python 3.8+
- 다운로드 엔진: yt-dlp
- HTTP 요청: requests, fake-useragent
- 구성 관리: configparser

## 파일 구조

```
HCL_Poker_Clips/
├── src/
│   ├── download/
│   │   └── main.py          # 메인 다운로드 스크립트
│   ├── utils/
│   │   └── youtube_utils.py # YouTube 관련 유틸리티
│   └── config/
│       └── config.py        # 설정 관리
├── requirements.txt         # 의존성 라이브러리
├── config.ini             # 설정 파일
├── run_downloader.py      # 실행 스크립트
├── hcl_poker_clips_downloader.log  # 로그 파일
└── downloads/             # 다운로드된 파일 저장 디렉토리
```

## 유튜브 정책 회피 전략

- 시그니처 난독화 대응
- 속도 제한 회피 (요청 간격 조절)
- 사용자 에이전트 무작위 변경
- 재시도 로직 (지수 백오프 방식)

## 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 설정 파일 확인

`config.ini` 파일을 열어 원하는 설정을 조정합니다:

```ini
[DEFAULT]
DOWNLOAD_DIR = downloads
MAX_RETRIES = 3
YTDLP_FORMAT = best[height<=1080]
```

### 3. 수동 URL 추가 (옵션)

YouTube의 자동 추출이 작동하지 않을 경우, `manual_urls.txt` 파일을 이용하여 수동으로 다운로드할 URL을 추가할 수 있습니다:

```
# 수동으로 추가할 YouTube 동영상 URL 목록
# 각 줄에 하나의 URL을 입력하세요
https://www.youtube.com/watch?v=VIDEO_ID
https://www.youtube.com/watch?v=ANOTHER_VIDEO_ID
```

### 4. 앱 실행

```bash
python run_downloader.py
```

### 5. 환경변수를 통한 설정 (선택사항)

필요한 경우 환경변수를 설정하여 실행할 수 있습니다:

```bash
export DOWNLOAD_DIR="./my_videos"
export MAX_RETRIES=5
python run_downloader.py
```

## 중요 정보

### YouTube 정책 회피 전략

이 앱은 YouTube의 자동화 방지 정책을 우회하기 위한 다양한 전략을 포함하고 있습니다:

- 요청 간격 조절 (랜덤 대기)
- 사용자 에이전트 회전
- 쿠키 및 세션 관리
- 회피 가능한 형식 선택

### 쿠키 사용 방법 (중요)

YouTube의 봇 탐지 정책이 강화되어 쿠키 없이 동영상을 다운로드하지 못하는 경우가 많습니다. 쿠키를 사용하면 더 높은 성공률을 얻을 수 있습니다.

1. Chrome 브라우저에서 YouTube에 로그인합니다.
2. `chrome://extensions/` 페이지에서 "Get cookies.txt" 확장 프로그램을 설치합니다.
3. 확장 프로그램을 사용하여 `cookies.txt` 파일을 다운로드합니다.
4. 이 파일을 프로젝트 루트에 `cookies.txt`로 저장합니다.
5. `src/config/config.py` 파일에서 `YTDLP_OPTIONS`에 `--cookies` 옵션을 추가합니다:

```python
# yt-dlp 설정
YTDLP_OPTIONS = {
    # ... 기존 설정 ...
    'cookies': 'cookies.txt',  # 쿠키 파일 경로 추가
}
```

### 자동 추출의 한계

YouTube의 정책 강화로 인해 채널에서 동영상을 자동으로 추출하지 못할 수 있습니다. 이 경우 수동으로 URL을 `manual_urls.txt` 파일에 추가하여 다운로드할 수 있습니다.

### 성능 최적화

- 다운로드 속도를 높이기 위해 회피 전략의 강도를 조절할 수 있습니다
- 설정 파일에서 `YTDLP_FORMAT`을 변경하여 화질을 조절할 수 있습니다
- `MAX_RETRIES`를 조정하여 실패 시 재시도 횟수를 변경할 수 있습니다

## 설정 옵션

| 설정 | 설명 | 기본값 |
|------|------|--------|
| DOWNLOAD_DIR | 다운로드 파일 저장 위치 | downloads |
| MAX_RETRIES | 다운로드 실패 시 재시도 횟수 | 3 |
| YTDLP_FORMAT | 다운로드 화질 설정 | best[height<=1080] |
| REQUEST_DELAY_MIN | 요청 최소 대기 시간 (초) | 1.0 |
| REQUEST_DELAY_MAX | 요청 최대 대기 시간 (초) | 3.0 |
| MAX_DELAY_SECONDS | 재시도 시 최대 대기 시간 (초) | 15.0 |
| LOG_LEVEL | 로그 레벨 | INFO |

## 기여

기여는 환영합니다. 문제 보고나 PR 요청을 언제나 환영합니다.

## 라이선스

이 소프트웨어는 개인 학습 및 연구 목적으로 개발되었습니다. YouTube의 이용 약관을 준수하면서 사용하시기 바랍니다.