# HCL Poker Clips 시스템 설정 가이드

이 가이드는 YouTube API와 Google Sheets를 연동하여 데이터를 자동으로 수집하기 위한 설정 방법을 설명합니다.

## 1. YOUTUBE_API_KEY 발급
1. [Google Cloud Console](https://console.cloud.google.com/) 접속
2. 프로젝트 생성/선택
3. **API 및 서비스 > 라이브러리**에서 `YouTube Data API v3` 활성화
4. **사용자 인증 정보 > 사용자 인증 정보 만들기 > API 키** 생성
5. 생성된 키를 `.env` 파일의 `YOUTUBE_API_KEY`에 입력

## 2. 구글 시트 구조 (Video Matrix)
데이터는 다음과 같은 매트릭스 형태로 정렬됩니다:
- **Video ID**: 유튜브 비디오 고유 코드
- **Title**: 비디오 제목 (영상 링크 하이퍼링크 포함)
- **PublishedAt**: 게시 일자
- **Playlist Columns (12개)**: 각 컬럼은 재생목록 제목이며, 해당 영상이 포함되어 있으면 `TRUE`(체크박스)로 표시됩니다.

## 3. GOOGLE_SHEET_ID 확인
1. 관리할 구글 시트 접속
2. URL 확인: `https://docs.google.com/spreadsheets/d/[이부분이_ID_입니다]/edit`
3. 해당 ID를 `.env` 파일의 `GOOGLE_SHEET_ID`에 입력

## 3. 서비스 계정 권한 설정 (EMAIL & PRIVATE_KEY)
1. Google Cloud Console의 **IAM 및 관리자 > 서비스 계정** 이동
2. **서비스 계정 만들기** 클릭 및 생성
3. 생성된 이메일 주소를 복사하여 `.env`의 `GOOGLE_SERVICE_ACCOUNT_EMAIL`에 입력
4. **[필수]** 구글 시트 오른쪽 상단 **공유** 버튼 클릭 -> 서비스 계정 이메일 추가 및 **편집자** 권한 부여
5. 서비스 계정 클릭 > **키(Keys) 탭** > **새 키 만들기(JSON)**
6. 다운로드된 JSON 파일의 `private_key` 내용을 `.env`의 `GOOGLE_PRIVATE_KEY`에 입력

---

## 4. 실행 및 자동화
- **수동 동기화**: `node scripts/sync-youtube.js` 실행
- **자동화 설정**: Windows 작업 스케줄러에 등록하여 매일 오전 8시 실행 권장
