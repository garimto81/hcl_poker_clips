# HCL Poker Clips 자동 다운로드 앱 - 프로젝트 요약

## 프로젝트 개요
- **목표**: HCL Poker Clips 채널(https://www.youtube.com/@HCLPokerClips/videos)의 동영상을 자동으로 다운로드
- **주기**: 매일 자동 다운로드 (일일 스케줄링 기능 포함)
- **방식**: Python 기반 커맨드라인 애플리케이션
- **대응 전략**: 유튜브 정책 변경에 대한 회피 전략 포함

## 현재 구현된 기능

### 1. 설정 시스템
- config.ini 파일을 통한 설정 관리
- 환경변수를 통한 설정 오버라이드
- 다양한 회피 전략 옵션 포함

### 2. 동영상 검색 및 추출
- YouTubeUtils 클래스를 통한 동영상 검색 기능
- yt-dlp 라이브러리를 이용한 동영상 정보 추출
- 회피 전략 적용 (랜덤 딜레이, 사용자 에이전트 변경 등)

### 3. 다운로드 시스템
- yt-dlp를 사용한 동영상 다운로드
- 다운로드 재시도 로직
- 아카이브 기능 (중복 다운로드 방지)
- 화질 및 포맷 설정

### 4. 로깅 및 오류 처리
- 파일 및 콘솔 로깅
- 오류 발생 시 재시도 메커니즘
- 오류 로그 상세 기록

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
├── test_downloader.py     # 테스트 스크립트
├── README.md              # 사용법 설명
├── PROJECT_SUMMARY.md     # 현재 문서
└── downloads/             # 다운로드된 파일 저장 디렉토리
```

## 현재 문제점 및 해결 방안

### 문제: 동영상 URL 추출 실패
- **현상**: 채널에서 동영상 URL을 찾지 못함
- **원인**: YouTube의 페이지 구조 변경 또는 yt-dlp 옵션 문제
- **해결 방안**:
  1. yt-dlp 옵션 조정 (`extract_flat`, `playlist_items` 등)
  2. 채널 URL 대신 RSS 피드 사용 (https://www.youtube.com/feeds/videos.xml?channel_id=UC...)
  3. 공식 YouTube API 사용

### 회피 전략 구현 현황
- ✅ 요청 간격 조절 (랜덤 딜레이)
- ✅ 사용자 에이전트 무작위 변경
- ✅ 재시도 로직 (지수 백오프 방식)
- ⏳ 프록시 서버 회전 (미구현)
- ⏳ CAPTCHA 해결 시스템 (미구현)

## 향후 개선 방향

### 1. 동영상 검색 개선
- RSS 피드를 통한 동영상 목록 가져오기
- 공식 YouTube API 사용
- yt-dlp의 더 효과적인 옵션 사용

### 2. 회피 전략 강화
- 프록시 서버 풀 구현
- 더 정교한 사용자 에이전트 회전
- 요청 패턴 다양화

### 3. 안정성 향상
- 오류 감지 및 자동 복구
- 상태 모니터링
- 대체 다운로드 경로

### 4. 자동화 기능
- 스케줄러 통합 (cron 또는 Windows 태스크 스케줄러)
- 알림 시스템
- 성공률 통계

## 실행 방법

### 개발 환경 설정
```bash
pip install -r requirements.txt
```

### 앱 실행
```bash
python run_downloader.py
```

### 테스트 실행
```bash
python test_downloader.py
```

## 주요 의존성 라이브러리

- `yt-dlp`: YouTube 동영상 다운로드
- `fake-useragent`: 무작위 사용자 에이전트 생성
- `requests`: HTTP 요청 (yt-dlp에 의해 내부적으로 사용됨)
- `configparser`: 설정 파일 처리

## 중요 알림

이 애플리케이션은 YouTube의 이용 약관을 준수하는 범위 내에서 개인적인 연구 및 학습 목적으로 개발되었습니다. 상업적 이용이나 저작권 침해의 우려가 있는 경우 사용을 자제하시기 바랍니다.