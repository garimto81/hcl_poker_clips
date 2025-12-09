"""
HCL Poker Clips 동영상 다운로드 GUI 앱
Tkinter 기반의 그래픽 인터페이스 앱
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import os
import sys
from pathlib import Path

# GUI 앱에서 사용할 다운로드 기능 import
# 기존에 개발한 다운로드 모듈을 가져옵니다
try:
    # sys.path에 src 디렉토리 추가
    src_path = str(Path(__file__).parent.parent.parent / "src")
    sys.path.insert(0, src_path)

    from download.main import HCLPokerClipsDownloader
    from config.config import Config
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)


class VideoDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HCL Poker Clips 동영상 다운로더")
        self.root.geometry("700x500")

        # 다운로드 관련 변수 초기화
        self.downloader = None
        self.config = Config()

        # UI 구성
        self.create_widgets()

    def create_widgets(self):
        # 메인 프레임
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 제목 레이블
        title_label = ttk.Label(main_frame, text="HCL Poker Clips 동영상 다운로더", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # URL 입력 프레임
        url_frame = ttk.LabelFrame(main_frame, text="동영상 URL 입력", padding="10")
        url_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # URL 입력 레이블
        url_label = ttk.Label(url_frame, text="YouTube 동영상 URL:")
        url_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # URL 입력 필드
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, width=70)
        self.url_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        self.url_entry.bind('<Return>', lambda event: self.start_download())

        # 다운로드 버튼
        self.download_btn = ttk.Button(url_frame, text="다운로드", command=self.start_download)
        self.download_btn.grid(row=1, column=1)

        # 열 확장 설정
        url_frame.columnconfigure(0, weight=1)

        # 다운로드 디렉토리 선택 프레임
        dir_frame = ttk.LabelFrame(main_frame, text="다운로드 설정", padding="10")
        dir_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # 다운로드 디렉토리 레이블 및 경로 표시
        dir_label = ttk.Label(dir_frame, text="다운로드 폴더:")
        dir_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        # 현재 디렉토리 표시
        self.dir_var = tk.StringVar(value=str(self.config.get_download_dir()))
        self.dir_label = ttk.Label(dir_frame, textvariable=self.dir_var)
        self.dir_label.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        # 디렉토리 변경 버튼
        change_dir_btn = ttk.Button(dir_frame, text="폴더 변경", command=self.change_download_dir)
        change_dir_btn.grid(row=1, column=1)

        # 열 확장 설정
        dir_frame.columnconfigure(0, weight=1)

        # 진행 상황 프레임
        progress_frame = ttk.LabelFrame(main_frame, text="진행 상황", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))

        # 진행 상태 표시
        self.progress_var = tk.StringVar(value="대기 중...")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        # 진행 바
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))

        # 열 확장 설정
        progress_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)

        # 로그 프레임
        log_frame = ttk.LabelFrame(main_frame, text="로그", padding="10")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 로그 텍스트 영역
        self.log_text = tk.Text(log_frame, height=10, state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # 스크롤바
        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # 열/행 확장 설정
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # 상태바
        self.status_var = tk.StringVar(value="준비 완료")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))

    def log_message(self, message):
        """로그 메시지를 텍스트 영역에 추가"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # 항상 마지막 줄을 보여줌
        self.log_text.config(state=tk.DISABLED)

    def change_download_dir(self):
        """다운로드 디렉토리 변경"""
        new_dir = filedialog.askdirectory(initialdir=self.config.get_download_dir())
        if new_dir:
            self.dir_var.set(new_dir)
            self.log_message(f"다운로드 디렉토리를 {new_dir}로 변경했습니다.")

    def start_download(self):
        """다운로드 시작 (별도 쓰레드에서 실행)"""
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("오류", "다운로드할 URL을 입력해주세요.")
            return

        # URL 유효성 검사
        if not (url.startswith("http://") or url.startswith("https://")):
            messagebox.showerror("오류", "유효한 URL을 입력해주세요.")
            return

        # 쓰레드에서 다운로드 실행
        thread = threading.Thread(target=self.download_thread, args=(url,))
        thread.daemon = True
        thread.start()

    def download_thread(self, url):
        """다운로드를 수행하는 쓰레드 함수"""
        try:
            # UI 업데이트
            self.root.after(0, lambda: self.progress_var.set("다운로드 준비 중..."))
            self.root.after(0, lambda: self.progress_bar.start(10))
            self.root.after(0, lambda: self.download_btn.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.status_var.set("다운로드 중..."))

            # 로그 메시지
            self.root.after(0, lambda: self.log_message(f"다운로드 시작: {url}"))

            # 다운로더 생성 (임시 설정으로)
            config = Config()
            # 사용자 지정 다운로드 디렉토리 설정
            custom_dir = self.dir_var.get()
            if custom_dir and os.path.isdir(custom_dir):
                config.DOWNLOAD_DIR = custom_dir
            downloader = HCLPokerClipsDownloader(config=config)

            # 다운로드 실행
            success = downloader.download_video(url)

            # 결과에 따른 UI 업데이트
            if success:
                self.root.after(0, lambda: self.progress_var.set("다운로드 완료!"))
                self.root.after(0, lambda: self.log_message("다운로드 성공!"))
                self.root.after(0, lambda: messagebox.showinfo("성공", "동영상 다운로드가 완료되었습니다!"))
            else:
                self.root.after(0, lambda: self.progress_var.set("다운로드 실패"))
                self.root.after(0, lambda: self.log_message("다운로드 실패!"))
                self.root.after(0, lambda: messagebox.showerror("실패", "동영상 다운로드에 실패했습니다."))

        except Exception as e:
            # 오류 처리
            self.root.after(0, lambda: self.progress_var.set("오류 발생"))
            self.root.after(0, lambda: self.log_message(f"오류: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("오류", f"다운로드 중 오류가 발생했습니다:\n{str(e)}"))
        finally:
            # UI 복원
            self.root.after(0, lambda: self.progress_bar.stop())
            self.root.after(0, lambda: self.download_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_var.set("다운로드 완료"))

    def run(self):
        """GUI 앱 실행"""
        self.root.mainloop()


def main():
    """GUI 앱 실행 함수"""
    root = tk.Tk()
    app = VideoDownloaderApp(root)
    app.run()


if __name__ == "__main__":
    main()