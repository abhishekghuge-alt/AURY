# AURY Smart Media Downloader

## Overview
A high-performance Python-based media downloader (v1) with a Command Line Interface (CLI). Supports downloading videos, audio, and other media from platforms like YouTube, TikTok, and more via yt-dlp.

## Architecture
- **Language**: Python 3.12
- **CLI Framework**: `rich` (tables, progress bars, terminal styling)
- **Core Engine**: `yt-dlp` (primary downloader)
- **Database**: SQLite3 (WAL mode, foreign keys, triggers, views)
- **Entry Point**: `python3 main.py` → runs `cli/main.py`

## Project Structure
- `main.py` — root entry point, launches the CLI
- `cli/` — CLI interface
  - `main.py` — orchestrates the 9-step download flow
  - `ui.py` — all terminal UI output via rich
  - `settings.py` — settings menu
- `core/` — business logic
  - `config.py` — global settings, quality map, yt-dlp options
  - `database.py` — SQLite management (AuryDB class)
  - `downloader.py` — DownloadWorker with yt-dlp
  - `clipboard_watcher.py` — monitors clipboard for URLs
- `downloads/` — output folders: video, audio, images, documents, archives, others
- `aury.db` — SQLite database (auto-created on first run)

## Workflow
- **Type**: Console (interactive TUI)
- **Command**: `python3 main.py`
- **Output**: Terminal-based interactive menu

## Key Features
- Multi-quality video download (144p to 4K)
- Audio-only extraction (MP3 320kbps via ffmpeg)
- Download history with search/filter/export
- Subtitle download and embedding
- Scheduled downloads
- Clipboard URL detection
- Concurrent downloads (up to 8 workers)
- Duplicate detection

## Dependencies
Installed via pip (Linux-compatible subset):
- `yt-dlp`, `rich`, `pyperclip`, `requests`, `pillow`
- `python-dotenv`, `flask`, `flask-cors`, `psutil`, `schedule`, `tqdm`, `keyboard`

## Notes
- Windows-specific packages (pywin32, comtypes, PyQt5, customtkinter) are excluded — this runs on Linux/Replit
- ffmpeg is available in the Replit environment for audio extraction and format merging
- The GUI (`gui_main.py`) requires a desktop display and is not supported in this environment
