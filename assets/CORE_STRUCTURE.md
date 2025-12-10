# HCL Poker Clips 다운로더 프로젝트 핵심 구조

## 루트 디렉토리 (핵심 파일만 유지)
```
HCL_Poker_Clips/
├── run_downloader.py        # 메인 실행 파일
├── config.ini              # 설정 파일
├── cookies.txt             # 인증 쿠키
├── requirements.txt        # 파이썬 의존성
├── README.md               # 프로젝트 설명
├── LICENSE                 # 라이선스
└── .gitignore              # Git 무시 설정
```

## 소스 코드
```
src/                        # 소스 코드
├── config/
├── download/
├── gui/
└── utils/
```

## 문서
```
docs/                       # 공식 문서
├── Updated_PRD.md          # 제품 요구사항
├── Technical_Architecture.md # 기술 아키텍처
├── Fallback_Mechanisms.md  # 폴백 메커니즘
├── Playwright_Integration_Plan.md # Playwright 통합
├── Proxy_Rotation_Throttling.md # 프록시 회전
└── Implementation_Roadmap.md # 구현 로드맵
```

## 기타 폴더
```
assets/                     # 기타 문서 및 보조 파일
├── Architecture_Design.md
├── Evasion_Strategy.md
├── FINAL_REPORT.md
├── get_channel_info.py
├── MANUAL_URL_GUIDE.md
├── Product_Requirements_Document.md
├── PROJECT_SUMMARY.md
└── QWEN.md

tests/                      # 테스트 파일
└── test_downloader.py

downloads/                  # 다운로드된 파일
├── *.mp4
└── downloaded.txt

logs/                       # 로그 파일 (필요 시 생성)
```