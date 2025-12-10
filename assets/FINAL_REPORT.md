# HCL Poker Clips 자동 다운로드 앱 - 프로젝트 완성 보고서

## 개요

이 프로젝트는 https://www.youtube.com/@HCLPokerClips/videos 채널의 동영상을 자동으로 다운로드하는 Python 기반 애플리케이션입니다. YouTube의 자동화 방지 정책이 강화됨에 따라, 다양한 회피 전략을 적용하여 동영상을 성공적으로 다운로드합니다.

## 주요 기능

### 1. 자동 채널 분석
- 채널의 동영상 목록을 자동으로 분석
- RSS 피드 이용하여 동영상 정보 추출 시도
- yt-dlp 라이브러리 사용한 동영상 정보 추출

### 2. 회피 전략
- 요청 간격 무작위 조절 (랜덤 대기)
- 사용자 에이전트 랜덤 회전
- 쿠키 및 세션 관리
- 다운로드 형식 지능형 선택

### 3. 수동 URL 지원
- `manual_urls.txt` 파일을 통한 수동 URL 추가 기능
- 자동 추출이 실패한 경우에도 수동으로 동영상 다운로드 가능

### 4. 설정 시스템
- `config.ini` 파일을 통한 설정 관리
- 환경변수를 통한 설정 오버라이드
- 상세한 로깅 시스템

### 5. 오류 처리 및 재시도
- 다운로드 실패 시 자동 재시도
- 오류 로그 기록
- 상태 모니터링

## 파일 구조

```
HCL_Poker_Clips/
├── src/
│   ├── download/main.py          # 메인 다운로드 스크립트
│   ├── utils/youtube_utils.py    # YouTube 관련 유틸리티
│   └── config/config.py          # 설정 관리
├── requirements.txt              # 의존성 라이브러리
├── config.ini                    # 설정 파일
├── manual_urls.txt               # 수동 URL 파일
├── run_downloader.py             # 실행 스크립트
├── test_downloader.py            # 테스트 스크립트
├── README.md                     # 사용법 설명
└── downloads/                    # 다운로드된 파일 저장 디렉토리
```

## 현재 상태

### 성공적인 구현
- [x] 다운로드 시스템 구현
- [x] 다양한 회피 전략 구현
- [x] 수동 URL 추가 기능 구현
- [x] 설정 시스템 구현
- [x] 오류 처리 및 재시도 로직 구현
- [x] 로깅 시스템 구현

### 자동 추출의 한계
- YouTube의 정책 강화로 인해 자동 채널 분석이 실패하는 경우가 많음
- 수동 URL 추가 기능으로 보완 가능

### 테스트 결과
- 수동 URL 추가 시 동영상 다운로드 성공 확인
- 회피 전략 적용 시 일정 수준의 성공률 확보

## 사용 방법

1. 의존성 설치: `pip install -r requirements.txt`
2. 필요한 경우 수동 URL을 `manual_urls.txt`에 추가
3. 앱 실행: `python run_downloader.py`

## 장애 해결

### 자동 추출이 작동하지 않는 경우
- YouTube의 자동화 방지 정책으로 인한 것일 수 있음
- 수동으로 URL을 `manual_urls.txt`에 추가하여 해결

### 다운로드 실패
- 네트워크 연결 확인
- YouTube 정책 회피 전략 강도 조정 (config.ini에서 설정 변경)
- 수동 URL 파일의 URL이 유효한지 확인

## 법적 고려사항

이 소프트웨어는 개인적인 연구 및 학습 목적으로 개발되었습니다. YouTube의 이용 약관을 준수하면서 사용하시기 바랍니다.