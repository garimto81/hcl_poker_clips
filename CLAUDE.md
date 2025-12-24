# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run CLI downloader (downloads all HCL Poker Clips channel videos)
python run_downloader.py

# Run Flask web server (http://0.0.0.0:8080)
python -m src.gui.web_server

# NAS-Google Sheets Sync
python run_nas_sync.py                  # Basic sync (fuzzy matching + duplicate detection)
python run_nas_sync.py --dry-run        # Test run (no updates)
python run_nas_sync.py --verbose        # Debug logging
python run_nas_sync.py --status         # Check current status
python run_nas_sync.py --reset          # Reset all checkboxes then sync
python run_nas_sync.py --no-fuzzy       # Exact match only
python run_nas_sync.py --no-duplicates  # Disable duplicate detection
python run_nas_sync.py --threshold 0.90 # Set similarity threshold (default: 0.85)
python run_nas_sync.py --detect-duplicates-only  # Duplicate detection only
python run_nas_sync.py --nas-folder "X:\Custom\Path"  # Override NAS folder

# Duplicate File Cleanup (auto-delete)
python run_nas_sync.py --delete-duplicates           # Preview (dry-run)
python run_nas_sync.py --delete-duplicates --force   # Actually delete files
python run_nas_sync.py --cleanup-only                # Cleanup only (no sync)
python run_nas_sync.py --cleanup-similarity 0.90     # Filename similarity (default: 0.85)
python run_nas_sync.py --cleanup-size-variance 0.05  # Size variance (default: 0.10 = 10%)
python run_nas_sync.py --audit-log                   # View deletion audit log
python run_nas_sync.py --export-audit audit.csv      # Export audit log to CSV

# Run tests
python -m pytest tests/test_matching.py -v    # Matching module tests
python -m pytest tests/test_downloader.py -v  # Downloader tests
```

## Architecture

```
src/
├── config/config.py      # Configuration management (config.ini + env vars)
├── download/main.py      # HCLPokerClipsDownloader - core download engine
├── utils/youtube_utils.py # YouTubeUtils - video extraction & info retrieval
├── sync/                  # NAS-Google Sheets sync module
│   ├── sync_config.py    # SyncConfig - sync settings
│   ├── nas_client.py     # NASClient - NAS file system access
│   ├── sheets_client.py  # SheetsClient - Google Sheets API
│   ├── nas_sheets_sync.py # NASSheetsSync - main sync service
│   └── matching/          # Fuzzy matching & duplicate detection
│       ├── normalizer.py     # FilenameNormalizer - 3-level normalization
│       ├── fuzzy_matcher.py  # FuzzyMatcher - similarity matching (rapidfuzz)
│       └── duplicate_detector.py # DuplicateDetector - duplicate file detection
└── gui/
    ├── gui_app.py        # Tkinter desktop GUI
    └── web_server.py     # Flask web interface
```

### Download Flow

1. **Video URL Extraction** (fallback priority):
   - RSS feed extraction (fastest)
   - yt-dlp full extraction
   - yt-dlp simplified extraction

2. **Download** with retry logic (max 3 attempts, exponential backoff)

3. **Archive tracking** via `downloaded.txt` prevents re-downloads

### Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `Config` | `src/config/config.py` | Loads settings from config.ini |
| `HCLPokerClipsDownloader` | `src/download/main.py` | Main download orchestrator |
| `YouTubeUtils` | `src/utils/youtube_utils.py` | YouTube API wrapper (RSS, yt-dlp) |
| `SyncConfig` | `src/sync/sync_config.py` | NAS-Sheets sync settings |
| `NASClient` | `src/sync/nas_client.py` | NAS folder file scanner |
| `SheetsClient` | `src/sync/sheets_client.py` | Google Sheets API client |
| `NASSheetsSync` | `src/sync/nas_sheets_sync.py` | Main sync orchestrator |
| `FilenameNormalizer` | `src/sync/matching/normalizer.py` | 3-level filename normalization |
| `FuzzyMatcher` | `src/sync/matching/fuzzy_matcher.py` | Similarity-based matching (85% threshold) |
| `DuplicateDetector` | `src/sync/matching/duplicate_detector.py` | Duplicate file detection (95% threshold) |
| `DuplicateCleaner` | `src/sync/matching/duplicate_cleaner.py` | Auto-delete duplicates (85% + 10% size) |
| `DeletionAuditLog` | `src/sync/matching/deletion_audit.py` | Deletion audit logging (JSON) |

## Configuration

Edit `config.ini` for:
- `DOWNLOAD_DIR` - Output folder (default: `downloads/`)
- `YTDLP_FORMAT` - Video quality (default: `best[height<=1080]`)
- Request delays and retry settings
- Proxy configuration (disabled by default)

### [SHEETS_SYNC] Section

| Setting | Description |
|---------|-------------|
| `NAS_FOLDER` | NAS folder path (default: `X:\GGP Footage\HCL Clips`) |
| `CREDENTIALS_PATH` | Google Service Account JSON path |
| `SPREADSHEET_ID` | Google Sheets ID |
| `SHEET_NAME` | Target sheet name (default: `HCL_Clips`) |
| `TITLE_COLUMN` | Title column for matching (default: `B`) |
| `CHECKBOX_COLUMN` | NAS checkbox column (default: `P`) |
| `DATE_COLUMN` | Downloaded date column (default: `Q`) |
| `SUBFOLDER_COLUMN` | Subfolder path column (default: `R`) |
| `PATH_COLUMN` | Full NAS path with hyperlink (default: `S`) |
| `DUPLICATE_COLUMN` | Duplicate marker column (default: `T`) |
| `FUZZY_ENABLED` | Enable fuzzy matching (default: `True`) |
| `SIMILARITY_THRESHOLD` | Fuzzy match threshold 0.0-1.0 (default: `0.85`) |
| `DUPLICATE_DETECTION` | Enable duplicate detection (default: `True`) |
| `DUPLICATE_THRESHOLD` | Duplicate detection threshold (default: `0.95`) |

### [DUPLICATE_CLEANUP] Section

| Setting | Description |
|---------|-------------|
| `CLEANUP_ENABLED` | Enable auto-cleanup (default: `False` for safety) |
| `CLEANUP_SIMILARITY_THRESHOLD` | Filename similarity for cleanup (default: `0.85`) |
| `CLEANUP_SIZE_VARIANCE` | Max size difference (default: `0.10` = 10%) |
| `CLEANUP_AUDIT_LOG` | Audit log path (default: `logs/deletion_audit.json`) |
| `CLEANUP_REQUIRE_CONFIRMATION` | Require confirmation (default: `True`) |

### Matching Algorithm

The sync uses a 3-stage matching strategy:

1. **Exact Match** (score=1.0): Basic normalization (lowercase + space removal)
2. **Normalized Match** (score=0.95): Standard normalization (remove all special chars)
3. **Fuzzy Match** (score≥0.85): Similarity matching using rapidfuzz

### Duplicate Detection

- Detects files with 95%+ similarity (e.g., `video.mp4` and `video (1).mp4`)
- Keeps the newest file, marks older duplicates in T column
- Each duplicate group: newest file = unmarked, others = T column TRUE

### Duplicate Cleanup (Auto-Delete)

**Detection Criteria:**
1. Filename similarity >= 85% (configurable)
2. File size difference <= 10% (configurable)

**Safety Mechanisms:**
- Default: dry-run mode (preview only)
- Requires `--force` flag for actual deletion
- Confirmation prompt (type 'DELETE' to confirm)
- All deletions logged to `logs/deletion_audit.json`

## Important Files

| File | Purpose |
|------|---------|
| `config.ini` | Main configuration |
| `downloads/downloaded.txt` | Archive list (duplicate prevention) |
| `manual_urls.txt` | Custom URLs to include in downloads |
| `cookies.txt` | Browser cookies for authentication (optional) |
| `run_nas_sync.py` | NAS-Sheets sync CLI entry point |

## Anti-Blocking

The project uses multiple evasion strategies:
- Random user agents (`fake-useragent`)
- Request delays (5-15 seconds)
- Multiple YouTube client spoofing (android, web_creator, web_embedded)
- Geo-bypass enabled
