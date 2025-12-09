"""
HCL Poker Clips 채널 정보 확인 스크립트
"""

import yt_dlp
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_channel_info():
    """HCL Poker Clips 채널 정보 가져오기"""
    channel_url = "https://www.youtube.com/@HCLPokerClips/videos"
    
    ydl_opts = {
        'quiet': False,
        'dump_single_json': True,  # 정보만 추출하고 다운로드하지 않음
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            
            print("채널 정보:")
            print(f"ID: {info.get('id', 'N/A')}")
            print(f"제목: {info.get('title', 'N/A')}")
            print(f"웹페이지 URL basename: {info.get('webpage_url_basename', 'N/A')}")
            print(f"웹페이지 URL: {info.get('webpage_url', 'N/A')}")
            print(f"작성자: {info.get('uploader', 'N/A')}")
            print(f"업로더 ID: {info.get('uploader_id', 'N/A')}")
            print(f"업로더 URL: {info.get('uploader_url', 'N/A')}")
            print(f"조회수: {info.get('view_count', 'N/A')}")
            print(f"구독자 수: {info.get('subscriber_count', 'N/A')}")
            
            # 채널 ID를 기반으로 RSS 피드 URL 생성 방법 확인
            if info.get('uploader_id'):
                print(f"RSS 피드 URL (업로더 ID 기반): https://www.youtube.com/feeds/videos.xml?user={info['uploader_id']}")
                
            if info.get('id') and info.get('webpage_url_basename') == 'channel':
                print(f"RSS 피드 URL (채널 ID 기반): https://www.youtube.com/feeds/videos.xml?channel_id={info['id']}")
            
            if 'entries' in info and info['entries']:
                print(f"\n최근 동영상 (샘플):")
                for i, entry in enumerate(info['entries'][:3]):  # 처음 3개만 표시
                    print(f"  {i+1}. 제목: {entry.get('title', 'N/A')}")
                    print(f"     URL: {entry.get('webpage_url', 'N/A')}")
                    print(f"     ID: {entry.get('id', 'N/A')}")
                    print()
    
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    get_channel_info()