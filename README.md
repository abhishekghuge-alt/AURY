# 🔴 AURY — Smart Media Downloader V2

AURY is a high-performance, modern media downloader built with Python. It features a sleek GUI, advanced analytics, and a robust DBMS backend for tracking your download history and statistics.

## 🚀 Quick Install (Windows)
1. Ensure **Python 3.10+** is installed.
2. Double-click `install.bat`.
3. Launch AURY from the **AURY.bat** shortcut on your Desktop.

## 🛠 Usage
### GUI (Recommended)
```powershell
python gui_main.py
```
- **Drag & Drop**: Drag a URL or a `.txt` file into the app.
- **Analytics**: View your download trends and platform distribution.
- **Smart Queue**: Reorder and manage active downloads in real-time.

### CLI
```powershell
python main.py
```
- High-speed terminal interface with rich tables and progress bars.

## ✨ Features
| Feature | Description |
| :--- | :--- |
| **Smart Queue** | Prioritize downloads with real-time reordering. |
| **Analytics** | Interactive charts (Donut & Bar) showing platform/quality split. |
| **Drag & Drop** | Support for browser URLs and batch .txt files. |
| **Thumbnail Preview** | See video title, duration, and image before downloading. |
| **DB Report** | Advanced SQL query runner and ER diagram for college presentation. |
| **System Tray** | Runs in the background; downloads continue when closed. |
| **Turbo Mode** | Auto-integrates with `aria2c` for 3x faster speeds. |

## 🏗 Database Schema (DBMS Project)
AURY uses SQLite with a relational schema optimized for performance:
- **`downloads`**: Core table storing file metadata, paths, and status.
- **`platforms`**: Tracks origin (YouTube, Instagram, etc.) via platform IDs.
- **`sessions`**: Groups downloads by application session for speed/success tracking.
- **`tags`**: N:M relationship for organizing downloads via `download_tags`.
- **`settings`**: Key-value store for application configuration and themes.

---
*Created for Advanced Agentic Coding - V2 Stable Release*
