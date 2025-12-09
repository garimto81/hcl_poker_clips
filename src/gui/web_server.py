"""
HCL Poker Clips 다운로더 웹 서버
Flask 기반의 웹 인터페이스
"""

from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import threading
import os
import sys
from pathlib import Path
import json
import time

# 프로젝트 경로 추가
project_root = str(Path(__file__).parent.parent.parent)  # 프로젝트 루트 디렉토리
sys.path.insert(0, project_root)

try:
    from src.download.main import HCLPokerClipsDownloader
    from src.config.config import Config
    from src.utils.youtube_utils import YouTubeUtils
except ImportError as e:
    print(f"Import error: {e}")
    # 임시로 모듈이 없는 경우를 위한 더미 클래스 생성
    class Config:
        DOWNLOAD_DIR = "downloads"
        MAX_RETRIES = 3
        REQUEST_DELAY_MIN = 1.0
        REQUEST_DELAY_MAX = 3.0
        YOUTUBE_CHANNEL_URL = "https://www.youtube.com/@HCLPokerClips/videos"

        @classmethod
        def get_download_dir(cls):
            return Path(cls.DOWNLOAD_DIR)

    class YouTubeUtils:
        def get_video_urls_from_channel(self, channel_url):
            # 테스트를 위한 더미 함수
            return ["https://www.youtube.com/watch?v=dummy123"]

        def get_video_urls_from_playlist(self, playlist_url):
            # 재생 목록 URL에서 동영상 URL 추출 (yt-dlp 사용)
            try:
                import yt_dlp
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(playlist_url, download=False)

                    if 'entries' in info:
                        video_urls = []
                        for entry in info['entries']:
                            if entry and 'webpage_url' in entry:
                                video_urls.append(entry['webpage_url'])
                        return video_urls
                    else:
                        return []

            except Exception as e:
                print(f"재생 목록에서 동영상 URL 추출 실패: {e}")
                return []

app = Flask(__name__)

# 전역 다운로더 인스턴스
downloader_instance = None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HCL Poker Clips 다운로더</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="url"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .progress-container {
            display: none;
            margin-top: 20px;
        }
        .progress-bar {
            width: 100%;
            height: 20px;
            background-color: #f0f0f0;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            background-color: #4CAF50;
            width: 0%;
            transition: width 0.3s ease;
        }
        .status {
            margin-top: 10px;
            padding: 10px;
            border-radius: 5px;
            display: none;
        }
        .status-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status-error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .log {
            margin-top: 20px;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 5px;
            max-height: 200px;
            overflow-y: auto;
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>HCL Poker Clips 다운로더</h1>

        <form id="downloadForm">
            <div class="form-group">
                <label for="url">YouTube 동영상 또는 재생 목록 URL:</label>
                <input type="url" id="url" name="url" placeholder="https://www.youtube.com/watch?v=... 또는 재생 목록 URL" required>
            </div>

            <button type="submit">다운로드 시작</button>
        </form>

        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div id="progressText">0%</div>
        </div>

        <div class="status" id="status"></div>

        <div class="log" id="logContainer">로그가 여기에 표시됩니다...</div>
    </div>

    <script>
        document.getElementById('downloadForm').addEventListener('submit', function(e) {
            e.preventDefault();

            const urlInput = document.getElementById('url');
            const url = urlInput.value.trim();
            if (!url) {
                alert('URL을 입력해주세요.');
                return;
            }

            // UI 업데이트
            document.getElementById('progressContainer').style.display = 'block';
            document.getElementById('status').style.display = 'none';
            document.getElementById('progressFill').style.width = '0%';
            document.getElementById('progressText').textContent = '0%';
            document.getElementById('logContainer').textContent = '';
            updateLog('다운로드 시작 중...');

            // AJAX 요청
            fetch('/api/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({url: url})
            })
            .then(response => response.json())
            .then(data => {
                document.getElementById('progressFill').style.width = '100%';
                document.getElementById('progressText').textContent = '100%';

                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';

                if (data.success) {
                    statusDiv.className = 'status status-success';
                    statusDiv.textContent = '다운로드 성공! ' + (data.message || '');
                    updateLog('성공: ' + data.message);
                } else {
                    statusDiv.className = 'status status-error';
                    statusDiv.textContent = '다운로드 실패! ' + (data.message || '');
                    updateLog('실패: ' + data.message);
                }
            })
            .catch(error => {
                document.getElementById('progressFill').style.width = '0%';
                document.getElementById('progressText').textContent = '0%';

                const statusDiv = document.getElementById('status');
                statusDiv.style.display = 'block';
                statusDiv.className = 'status status-error';
                statusDiv.textContent = '오류 발생: ' + error.message;
                updateLog('오류: ' + error.message);
            });
        });

        function updateLog(message) {
            const logContainer = document.getElementById('logContainer');
            const currentTime = new Date().toLocaleTimeString(); // HH:MM:SS 형식
            logContainer.textContent = `[${currentTime}] ${message}\\n` + logContainer.textContent;
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/favicon.ico')
def favicon():
    # favicon 없이 204 상태 코드 반환 (no-content)
    return '', 204

@app.route('/api/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        url = data.get('url', '').strip()

        if not url:
            return jsonify({'success': False, 'message': 'URL을 입력해주세요.'}), 400

        # URL이 재생 목록인지 확인
        is_playlist = 'playlist' in url or 'list=' in url

        # 다운로드 인스턴스 생성
        config = Config()
        downloader_instance = HCLPokerClipsDownloader(config=config)

        # 로그 업데이트
        current_time = time.strftime('%H:%M:%S')
        log_msg = f"[{current_time}] 다운로드 시작: {url}"
        if is_playlist:
            log_msg += " (재생 목록)"

        print(log_msg)

        # 재생 목록인 경우
        if is_playlist:
            # YouTubeUtils를 사용하여 재생 목록에서 동영상 URL 목록 가져오기
            try:
                # yt-dlp를 사용하여 재생 목록에서 동영상 URL 추출
                import yt_dlp
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                    'extract_flat': True,
                }

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(url, download=False)
                    video_urls = []
                    if 'entries' in result:
                        for entry in result['entries']:
                            if entry and 'webpage_url' in entry:
                                video_urls.append(entry['webpage_url'])
                    elif 'webpage_url' in result:
                        # 재생목록이 아닌 단일 비디오일 경우
                        video_urls = [result['webpage_url']]
            except Exception as e:
                print(f"재생 목록 URL 추출 실패: {str(e)}")
                return jsonify({'success': False, 'message': f'재생 목록에서 동영상 URL을 가져오지 못했습니다: {str(e)}'}), 500

            if not video_urls:
                return jsonify({'success': False, 'message': '재생 목록에서 동영상을 찾을 수 없습니다.'}), 400

            # 각 동영상 다운로드
            results = []
            for i, video_url in enumerate(video_urls):
                current_time = time.strftime('%H:%M:%S')
                print(f"[{current_time}] 재생 목록 #{i+1}/{len(video_urls)} 다운로드 중: {video_url}")

                # 진행률 업데이트 (UI에서는 실시간 진행률 표시 불가능하지만 서버 로그로 기록)
                progress = int(((i + 1) / len(video_urls)) * 100)

                # 실제 다운로드 수행
                success = downloader_instance.download_video(video_url)
                results.append({'url': video_url, 'success': success})

                # 로그 업데이트
                status = "성공" if success else "실패"
                print(f"[{current_time}] 재생 목록 #{i+1}/{len(video_urls)} {status}: {video_url}")

            success_count = sum(1 for r in results if r['success'])
            message = f"재생 목록 다운로드 완료: {success_count}/{len(results)} 동영상 다운로드 성공"
            return jsonify({'success': True, 'message': message, 'results': results})
        else:
            # 단일 동영상 다운로드
            success = downloader_instance.download_video(url)

            if success:
                return jsonify({'success': True, 'message': f'동영상 다운로드 완료: {url}'})
            else:
                return jsonify({'success': False, 'message': f'동영상 다운로드 실패: {url}'}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': f'오류 발생: {str(e)}'}), 500

if __name__ == '__main__':
    # 서버를 0.0.0.0 주소로 실행하여 로컬 네트워크에서 접근 가능하게 함
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)