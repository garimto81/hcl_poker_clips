# HCL Poker Clips 동영상 수동 URL 추가 가이드

이 파일은 HCL Poker Clips 채널에서 직접 동영상 URL을 찾아 수동으로 추가하는 방법을 안내합니다.

## 동영상 URL 찾는 방법

1. 웹 브라우저에서 다음 주소를 엽니다:
   https://www.youtube.com/@HCLPokerClips/videos

2. 동영상 썸네일 중 가장 최근 것(일반적으로 제일 위)을 클릭합니다.

3. 동영상이 재생되는 페이지의 주소(URL)을 복사합니다.
   - 주소는 일반적으로 `https://www.youtube.com/watch?v=`로 시작합니다.
   - 예: `https://www.youtube.com/watch?v=VIDEO_ID`

4. 복사한 URL을 아래 형식에 맞게 `manual_urls.txt` 파일에 추가합니다:

```
https://www.youtube.com/watch?v=VIDEO_ID
```

## 예시

```
# 수동으로 추가할 HCL Poker Clips 동영상 URL 목록
# 각 줄에 하나의 URL을 입력하세요

https://www.youtube.com/watch?v=CfBKD-ABD_s
https://www.youtube.com/watch?v=ANOTHER_VIDEO_ID
```

## 참고 사항

- 여러 동영상을 추가하려면 각 줄에 하나씩 URL을 추가하세요.
- 주석은 `#`으로 시작합니다.
- 동영상이 삭제되었거나 접근 불가능한 경우 다운로드가 실패할 수 있습니다.