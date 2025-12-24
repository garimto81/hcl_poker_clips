# HCL Poker Clips 자동 다운로더

이 프로젝트는 YouTube 채널 "HCL Poker Clips"의 동영상을 자동으로 다운로드하는 애플리케이션입니다.

## 프로젝트 구조

```
HCL_Poker_Clips/
├── src/                    # 소스 코드
│   ├── config/             # 설정 모듈
│   ├── download/           # 다운로드 로직
│   ├── sync/               # NAS-Google Sheets 동기화 모듈
│   │   └── matching/       # 유사도 매칭 & 중복 감지
│   ├── gui/                # GUI 및 웹 인터페이스
│   └── utils/              # 유틸리티 함수
├── tests/                  # 테스트 파일
├── docs/                   # 문서 파일
├── downloads/              # 다운로드된 파일 저장
├── config.ini              # 설정 파일
├── cookies.txt             # 인증 쿠키
├── run_downloader.py       # 다운로드 실행 파일
├── run_nas_sync.py         # NAS-Sheets 동기화 실행 파일
├── requirements.txt        # 의존성
└── README.md               # 이 파일
```

## 핵심 기능

- HCL Poker Clips 채널 동영상 자동 다운로드
- 다양한 회피 전략을 통한 차단 회피
- GUI 및 웹 인터페이스 제공
- **NAS-Google Sheets 동기화**: NAS 폴더의 다운로드된 파일을 Google Sheets와 자동 동기화
  - **유사도 매칭**: 파일명과 시트 제목이 정확히 일치하지 않아도 85% 이상 유사하면 매칭
  - **중복 파일 감지**: 95% 유사도로 중복 파일 감지, T열에 체크박스로 표시

## 사용 방법

### 다운로드
1. 의존성 설치: `pip install -r requirements.txt`
2. 쿠키 파일 확보: 브라우저에서 로그인 후 cookies.txt 파일 생성
3. 실행: `python run_downloader.py`

### NAS-Sheets 동기화
NAS 폴더의 파일을 Google Sheets와 동기화합니다. **유사도 매칭**과 **중복 파일 감지** 기능을 지원합니다.

```bash
# 기본 동기화 (유사도 매칭 + 중복 감지 활성화)
python run_nas_sync.py

# 테스트 실행 (실제 업데이트 없음)
python run_nas_sync.py --dry-run

# 전체 초기화 후 동기화
python run_nas_sync.py --reset

# 상태 확인
python run_nas_sync.py --status

# 유사도 매칭 비활성화 (정확 일치만)
python run_nas_sync.py --no-fuzzy

# 유사도 임계값 설정 (기본: 0.85)
python run_nas_sync.py --threshold 0.90

# 중복 감지만 실행
python run_nas_sync.py --detect-duplicates-only

# 중복 보고서 저장
python run_nas_sync.py --duplicate-report report.txt
```

**동기화 동작:**
- NAS 폴더의 파일명과 시트의 B열(Title) 매칭 (하위 폴더 포함)
- **3단계 매칭**: 정확 일치 → 정규화 일치 → 유사도 매칭 (85%)
- 매칭된 행의 P열(NAS) 체크박스를 TRUE로 변경
- 매칭된 행의 Q열(DownloadedAt)에 **파일의 실제 다운로드 날짜** 입력
- **중복 파일 감지**: 95% 유사도로 중복 파일 감지, T열에 체크박스로 표시

**컬럼 매핑:**
| 컬럼 | 용도 |
|------|------|
| B | Title (매칭 기준) |
| P | NAS 다운로드 체크박스 |
| Q | 다운로드 날짜 |
| R | 서브폴더 |
| S | NAS 경로 (하이퍼링크) |
| T | 중복 파일 체크박스 |

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