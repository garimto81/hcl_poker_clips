#!/usr/bin/env python3
"""
HCL Poker Clips YouTube 동영상 자동 다운로드 앱
실행 스크립트
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
src_dir = project_root / "src"
sys.path.insert(0, str(src_dir))

from src.download.main import main

if __name__ == "__main__":
    main()