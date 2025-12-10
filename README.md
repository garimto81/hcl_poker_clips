# HCL Poker Clips 자동 다운로더

이 프로젝트는 YouTube 채널 "HCL Poker Clips"의 동영상을 자동으로 다운로드하는 애플리케이션입니다.

## 프로젝트 구조

```
HCL_Poker_Clips/
├── src/                    # 소스 코드
│   ├── config/             # 설정 모듈
│   ├── download/           # 다운로드 로직
│   ├── gui/                # GUI 및 웹 인터페이스
│   └── utils/              # 유틸리티 함수
├── docs/                   # 문서 파일
├── downloads/              # 다운로드된 파일 저장
├── config.ini              # 설정 파일
├── cookies.txt             # 인증 쿠키
├── run_downloader.py       # 메인 실행 파일
├── requirements.txt        # 의존성
└── README.md               # 이 파일
```

## 핵심 기능

- HCL Poker Clips 채널 동영상 자동 다운로드
- 다양한 회피 전략을 통한 차단 회피
- GUI 및 웹 인터페이스 제공

## 사용 방법

1. 의존성 설치: `pip install -r requirements.txt`
2. 쿠키 파일 확보: 브라우저에서 로그인 후 cookies.txt 파일 생성
3. 실행: `python run_downloader.py`

## 주요 제약사항

2025년 12월 10일 기준으로, YouTube의 강력한 보안 정책으로 인해 완전한 자동화가 어렵습니다. 수동적인 쿠키 갱신 및 브라우저 세션 유지가 필요할 수 있습니다.

## 문서

자세한 기술 문서는 `docs/` 폴더에서 확인할 수 있습니다:
- `Updated_PRD.md`: 제품 요구사항 문서
- `Technical_Architecture.md`: 기술 아키텍처
- `Fallback_Mechanisms.md`: 폴백 메커니즘
- `Playwright_Integration_Plan.md`: Playwright 통합 계획
- `Proxy_Rotation_Throttling.md`: 프록시 회전 및 요청 조절
- `Implementation_Roadmap.md`: 구현 로드맵