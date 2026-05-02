# AURY Smart Media Downloader

## Overview
A high-performance Python-based media downloader with three interfaces: V1 CLI, V2 Desktop GUI, and V3 Web UI (primary). Supports downloading videos, audio, and other media from YouTube, TikTok, Instagram, SoundCloud, and more via yt-dlp.

## Architecture
- **Language**: Python 3.12
- **Web Server**: Flask + Flask-CORS (port 5000, SSE for live progress)
- **Frontend**: Vanilla JS + Tailwind CSS (CDN) + Lucide icons — single-page app with 13 pages
- **CLI Framework**: `rich` (tables, progress bars, terminal styling)
- **GUI Framework**: `customtkinter` + `tkinterdnd2` (desktop GUI, optional)
- **Core Engine**: `yt-dlp` (primary downloader)
- **Database**: SQLite3 (WAL mode, foreign keys, triggers, views) — `aury.db`
- **Entry Points**:
  - `python3 web_server.py` → **V3 Web UI** (browser-based, port 5000) ← **main workflow**
  - `python3 main.py` → V1 CLI interactive terminal
  - `python3 gui_main.py` → V2 GUI desktop app (requires display)

## Web UI Pages (V3 — all implemented)
1. **Dashboard** — stat cards, Quick Download input, auto-paste detection, thumbnail preview, download queue, live speed graph
2. **History** — searchable/filterable table, CSV export, delete records, pagination
3. **Analytics** — 14-day activity bar chart, quality split, platform split, speed history graph
4. **Batch Download** — paste up to 50 URLs at once, quality selector, audio-only toggle
5. **Scheduler** — schedule any download for a specific date/time with optional repeat
6. **File Manager** — browse, download, and delete files in the download folder
7. **Tag Manager** — create/delete tags, assign to downloads, filter by tag
8. **Platform Stats** — per-platform breakdown (total, completed, failed, data, avg speed)
9. **DB Report** — SQL query runner with 8 preset queries, CSV export, DB backup download
10. **ER Diagram** — SVG visual schema of all 7 tables with FK relationship arrows
11. **Notifications** — real-time alert log (success/error/warning/info), clear all
12. **Settings** — download folder, quality, workers, audio format, turbo mode, subtitles, PIN lock
13. **Auth / PIN** — PIN lock UI (enable/disable, set PIN, logout)

## Real-Time Features
- SSE (Server-Sent Events) on `/stream` — live queue updates and notifications without polling
- Live speed graph (Canvas API, 60-sample rolling line chart, gradient fill)
- Bottom task bar — always-visible active download progress bar, expandable
- Toast notifications — stacked at bottom-right, auto-dismiss after 4 seconds, 4 kinds
- Platform logo auto-detected (emoji from platforms table)
- Thumbnail preview in download modal and Quick Download (fetches via yt-dlp)
- Estimated file size shown before download
- Auto-paste detection — any URL copied to clipboard auto-fills Quick Download input

## Web API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/stats` | Dashboard stat cards |
| GET | `/api/history` | Filtered/paginated history |
| DELETE | `/api/history/<id>` | Delete one record |
| GET | `/api/queue` | Live download queue |
| POST | `/api/download` | Start a download |
| POST | `/api/queue/<key>/stop` | Stop a download |
| GET | `/api/analytics` | Charts data |
| GET/POST | `/api/settings` | Read/write settings |
| GET | `/api/info?url=` | URL metadata (title, thumbnail, size) |
| POST | `/api/batch` | Start batch of up to 50 downloads |
| GET/POST | `/api/scheduler` | List/add scheduled downloads |
| DELETE | `/api/scheduler/<id>` | Delete scheduled item |
| GET/POST | `/api/tags` | List/create tags |
| DELETE | `/api/tags/<id>` | Delete tag |
| GET/POST | `/api/downloads/<id>/tags` | Get/add tags for a download |
| DELETE | `/api/downloads/<id>/tags/<tag_id>` | Remove tag from download |
| GET | `/api/files` | List downloaded files |
| GET | `/api/files/<name>` | Download a file |
| DELETE | `/api/files/<name>` | Delete a file |
| POST | `/api/db-query` | Run a SELECT SQL query |
| GET | `/api/db-presets` | 8 preset report queries |
| GET | `/api/notifications` | Notification log |
| DELETE | `/api/notifications` | Clear notifications |
| GET | `/api/platform-stats` | Per-platform breakdown |
| GET | `/api/export/csv` | Download history as CSV |
| GET | `/api/export/db` | Download aury.db backup |
| GET | `/api/auth/status` | Auth enabled + session ok |
| POST | `/api/auth/login` | Login with PIN |
| POST | `/api/auth/logout` | Lock screen |
| POST | `/api/auth/set-pin` | Set or remove PIN |
| GET | `/stream` | SSE stream (queue_update, notification events) |

## Database Schema (7 tables)
1. **platforms** — id, name, icon, domain, created_at
2. **sessions** — id, started_at, ended_at, total_files, completed_files, failed_files, total_bytes, avg_speed_bps, duration_secs
3. **downloads** — id, session_id (FK), platform_id (FK), url, title, quality_label, status, file_path, file_size_bytes, avg_speed_bps, retry_count, last_error, downloaded_at, queue_position, …
4. **settings** — key (PK), value, updated_at
5. **tags** — id, name (UNIQUE)
6. **download_tags** — (download_id, tag_id) composite PK
7. **scheduled_downloads** — id, url, quality, scheduled_ts, repeat, fired, note, created_at

**Views**: `v_downloads_full`, `v_platform_stats`, `v_daily_activity`
**Triggers**: `trg_update_session_on_complete`, `trg_update_session_on_fail`, `trg_settings_updated`

## Project Structure
- `web_server.py` — Flask web server with all 28 API endpoints + SSE
- `templates/index.html` — Complete 13-page SPA (dark theme, Canvas charts, real-time)
- `main.py` — V1 CLI entry point
- `gui_main.py` — V2 GUI entry point (requires $DISPLAY)
- `core/config.py` — global settings, QUALITY_MAP, init_config(), clean_url()
- `core/database.py` — AuryDB class (all DB methods, migrations, scheduler, tags)
- `core/downloader.py` — DownloadWorker (yt-dlp engine, retry, aria2c)
- `core/clipboard_watcher.py` — clipboard URL watcher
- `cli/` — CLI interface (main.py, ui.py, settings.py)
- `gui/` — Desktop GUI components (V2)
- `static/favicon.ico` — app favicon
- `downloads/` — output folder (video, audio, images, …)
- `aury.db` — SQLite database (auto-created)

## Keyboard Shortcuts (Web UI)
- `Ctrl+N` — New Download modal
- `Ctrl+H` — History page
- `Ctrl+,` — Settings page
- `Ctrl+B` — Batch Download page
- `Escape` — Close modal

## Bug Fixes Applied (V1–V3)
1. `core/database.py` — Added `get_history()` wrapper
2. `core/config.py` — Added `init_config()` function
3. `cli/ui.py` — Added `from rich import box`, format helpers
4. `cli/main.py` — Fixed `platform` variable shadowing; fixed queue tuple index
5. `gui/dashboard.py` — Fixed `start_download()` + `_handle_progress()`
6. `gui_main.py` — Fixed tray icon callable
7. `gui/db_report.py` — Replaced `ctk.CTkCanvas` → `tk.Canvas`; optional `ImageGrab`
8. `web_server.py` — Fixed `get_filtered_history` param names (`search=` not `search_term=`)

## Desktop App (Windows — V4)

Uses `pywebview` to wrap the existing Flask app inside a native Windows window.
Zero frontend changes — the same `index.html` runs inside the window.

### Quick Start (Python required):
```
1. Clone repo to your Windows laptop
2. Run: install_desktop.bat   ← one-time setup, creates virtual env + Desktop shortcut
3. Run: run_desktop.bat       ← every time you want to open AURY
   OR:  double-click "AURY" shortcut on Desktop
```

### Build standalone .exe (no Python on target machine):
```
1. Run: build_desktop.bat
2. Find: dist\AURY.exe  (copy anywhere — fully portable)
```

### How it works:
```
run_desktop.bat
    ↓ sets AURY_DESKTOP=1
desktop_app.py
    ↓ starts Flask on 127.0.0.1:5000 (background thread)
    ↓ waits for server ready
    ↓ opens pywebview native window → http://127.0.0.1:5000/
Full AURY app appears in native window (no browser bar visible)
Downloads → Google Drive path (auto-detected) or ~/Downloads/AURY
```

### Google Drive download path (Windows):
```
C:\Users\DAR AL WEFAQ\Google Drive Streaming\My Drive\cllg\AURY\downloads
```
The app auto-detects this path via `IS_DESKTOP` flag in `core/config.py`.
If Google Drive Streaming isn't installed, falls back to `~/Downloads/AURY`.
Settings page → "Drive Path" button → pick from common path suggestions → Save.

### New files added:
- `desktop_app.py`          ← main entry point for desktop mode
- `build_desktop.bat`       ← builds dist/AURY.exe via PyInstaller
- `install_desktop.bat`     ← one-click setup + Desktop shortcut creation
- `run_desktop.bat`         ← quick launcher (double-click to open)
- `requirements_desktop.txt` ← desktop-specific dependencies

### Files modified for desktop support:
- `core/config.py`         ← IS_DESKTOP flag + Windows download path logic
- `requirements.txt`       ← added pywebview>=4.4.1
- `templates/index.html`   ← Drive Path button now shows path suggestions dropdown

---

## Keyboard Shortcuts (Web UI)
- `Ctrl+N` — New Download modal
- `Ctrl+H` — History page
- `Ctrl+,` — Settings page
- `Ctrl+B` — Batch Download page
- `Escape` — Close modal
- `S` *(ER Diagram)* — Select tool
- `H` / `Space` *(ER Diagram)* — Pan tool
- `F` *(ER Diagram)* — Fit all nodes in view
- `+` / `-` *(ER Diagram)* — Zoom in / out

## Bug Fixes Applied (V1–V3)
1. `core/database.py` — Added `get_history()` wrapper
2. `core/config.py` — Added `init_config()` function
3. `cli/ui.py` — Added `from rich import box`, format helpers
4. `cli/main.py` — Fixed `platform` variable shadowing; fixed queue tuple index
5. `gui/dashboard.py` — Fixed `start_download()` + `_handle_progress()`
6. `gui_main.py` — Fixed tray icon callable
7. `gui/db_report.py` — Replaced `ctk.CTkCanvas` → `tk.Canvas`; optional `ImageGrab`
8. `web_server.py` — Fixed `get_filtered_history` param names (`search=` not `search_term=`)
9. `core/downloader.py` — `_sort_destination()` now reads `config.DOWNLOAD_DIR` at call time (not import time) so runtime path changes take effect immediately

## Notes
- YouTube downloads require browser cookies in Replit/cloud environments — use Dailymotion or other platforms for testing
- ffmpeg is available in the environment for audio extraction and format merging
- GUI (`gui_main.py`) requires a desktop display and runs on Windows/macOS/Linux only
- aria2c turbo mode requires aria2c binary (not installed in this environment)
- The scheduler background thread checks every 30 seconds for pending scheduled downloads
- Desktop mode (`AURY_DESKTOP=1`) auto-selects the Google Drive download path on Windows
