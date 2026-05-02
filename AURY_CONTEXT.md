AURY PROJECT CONTEXT — attach this to every prompt

PROJECT: AURY Smart Media Downloader
LANGUAGE: Python 3.10+
CURRENT VERSION: V1 CLI (working)
TARGET: V2 CLI + V2 Desktop GUI

FOLDER STRUCTURE:
AURY/
├── main.py           ← V1 CLI entry
├── core/
│   ├── database.py   ← SQLite via AuryDB class
│   ├── downloader.py ← yt-dlp + aria2c workers
│   ├── config.py     ← settings + ydl opts
│   └── clipboard_watcher.py  (to be created)
├── cli/
│   ├── main.py       ← menus + session logic
│   ├── ui.py         ← Rich panels + progress
│   └── settings.py   (to be created)
├── gui/              (to be created in Phase 3)
└── aury.db           ← SQLite database

SHARED RULES (apply to ALL code you write):
- All DB access via: from core import database; database.db.method()
- Never use sqlite3 directly outside core/database.py
- Rich console = from rich.console import Console; console = Console()
- All y/n prompts must loop until valid input, blank = "n"
- No controls panel (P/R/S keyboard shortcuts removed)
- Suppress all yt-dlp cookie/DPAPI errors via _SilentLogger
- aria2c used if available (check shutil.which("aria2c"))
- Max 10 progress bar updates/second (throttle hook)

CURRENT DB STATUS: Fresh schema (AuryDB class, 5 tables)
CURRENT V1 STATUS: Working CLI with menu, download, history