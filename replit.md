# AURY Smart Media Downloader

## Overview
A high-performance Python-based media downloader with a V1 Command Line Interface (CLI) and V2 Desktop GUI. Supports downloading videos, audio, and other media from platforms like YouTube, TikTok, Instagram, SoundCloud, and more via yt-dlp.

## Architecture
- **Language**: Python 3.12
- **Web Server**: Flask + Flask-CORS (port 5000, SSE for live progress)
- **Frontend**: Vanilla JS + Tailwind CSS (CDN) + Lucide icons — single-page app
- **CLI Framework**: `rich` (tables, progress bars, terminal styling)
- **GUI Framework**: `customtkinter` + `tkinterdnd2` (desktop GUI, optional)
- **Core Engine**: `yt-dlp` (primary downloader)
- **Database**: SQLite3 (WAL mode, foreign keys, triggers, views)
- **Entry Points**:
  - `python3 web_server.py` → **V3 Web UI** (browser-based, port 5000) ← **main workflow**
  - `python3 main.py` → V1 CLI interactive terminal
  - `python3 gui_main.py` → V2 GUI desktop app (requires display)

## Project Structure
- `main.py` — root entry point, launches the CLI
- `cli/` — CLI interface
  - `main.py` — orchestrates the 9-step download flow
  - `ui.py` — all terminal UI output via rich
  - `settings.py` — settings menu (9 options)
- `core/` — business logic
  - `config.py` — global settings, quality map, yt-dlp options, `init_config()`, `clean_url()`
  - `database.py` — SQLite management (AuryDB class with 5 tables, views, triggers)
  - `downloader.py` — DownloadWorker with yt-dlp, aria2c turbo, retry engine
  - `clipboard_watcher.py` — monitors clipboard for URLs
- `gui/` — Desktop GUI (V2)
  - `app.py` — main window, sidebar nav, drag-and-drop, keyboard shortcuts, theme toggle
  - `dashboard.py` — download tab + analytics tab, live queue updates
  - `history.py` — searchable history table with open/delete actions
  - `settings.py` — GUI settings page
  - `download_modal.py` — URL modal with thumbnail preview, quality picker
  - `queue_panel.py` — smart download queue with reordering
  - `analytics.py` — analytics tab (weekly stats, activity chart, quality/platform split)
  - `charts.py` — custom BarChart and DonutChart (tkinter Canvas)
  - `db_report.py` — DB report with SQL runner, preset queries, schema viewer, ER diagram
  - `drop_overlay.py` — drag-and-drop overlay
  - `widgets.py` — NavButton, StatCard, ActiveDownloadCard
- `gui_main.py` — GUI entry point with system tray icon (pystray)
- `downloads/` — output folders: video, audio, images, documents, archives, others
- `aury.db` — SQLite database (auto-created on first run)

## Workflow
- **Type**: Console (interactive TUI)
- **Command**: `python3 main.py`
- **Output**: Terminal-based interactive menu

## Key Features (P-01 → P-16 all implemented)
- **P-01**: Quick Download mode (skip quality prompts, use default)
- **P-02**: Batch URL input + URL cleaner (strips tracking params)
- **P-03**: aria2c Turbo mode + auto-retry with exponential backoff (3 attempts)
- **P-04**: Full Settings menu (folder, quality, workers, turbo, subtitles, clear history, DB stats)
- **P-05**: History viewer upgrade (search, filter by platform/status, sort, paginate, CSV export)
- **P-06**: GUI speed fixes (threaded downloads, 150ms UI loop)
- **P-07**: Smart Queue Manager (reorder, pause, resume, stop, open, delete)
- **P-08**: Analytics Dashboard tab (14-day activity chart, quality/platform donut charts)
- **P-09**: Drag & Drop URL (tkinterdnd2 integration)
- **P-10**: Thumbnail preview in download modal (fetches via yt-dlp)
- **P-11**: Keyboard shortcuts (Ctrl+N, Ctrl+Q, Ctrl+H, Ctrl+,, Ctrl+D, F5, Ctrl+V, Escape)
- **P-12**: Dark/Light theme toggle (persisted in DB)
- **P-13**: DB Report screen (SQL runner, 8 preset queries, schema viewer, CSV export)
- **P-14**: ER Diagram generator (drawn on tk.Canvas, PNG export on Windows)
- **P-15**: System Tray icon (pystray, minimize-to-tray, active download count)
- **P-16**: One-click installer (install.bat for Windows)

## Bug Fixes Applied (this session)
1. `core/database.py` — Added `get_history()` wrapper (was missing, used by dashboard & history pages)
2. `core/config.py` — Added `init_config()` function (called by GUI settings page on save)
3. `cli/ui.py` — Added `from rich import box`, `format_size()`, `format_speed()` helpers
4. `cli/main.py` — Fixed `platform` variable shadowing the stdlib module in `_run_history()`; fixed wrong queue tuple index (was `[1]`, should be `[2]` for quality label)
5. `gui/dashboard.py` — Fixed broken `start_download()` (referenced undefined `w`); rewrote `_handle_progress()` to properly track workers and route to queue panel
6. `gui_main.py` — Fixed tray icon `on_open` calling `app.deiconify()` (passed result) instead of passing the callable
7. `gui/db_report.py` — Replaced non-existent `ctk.CTkCanvas` with `tk.Canvas`; made `ImageGrab` import gracefully optional

## Dependencies
Installed via pip (Linux-compatible subset):
- `yt-dlp`, `rich`, `pyperclip`, `requests`, `pillow`
- `python-dotenv`, `flask`, `flask-cors`, `psutil`, `schedule`, `tqdm`, `keyboard`
- `customtkinter`, `tkinterdnd2`, `pystray`

## Notes
- YouTube downloads require browser cookies in server/cloud environments — Dailymotion and other platforms work without authentication
- ffmpeg is available in the Replit environment for audio extraction and format merging
- The GUI (`gui_main.py`) requires a desktop display (`$DISPLAY`) and is not supported directly in this Replit environment — it runs on Windows/macOS/Linux desktops
- aria2c is not installed in this environment (would add turbo mode if present)
