"""
AURY Desktop App Entry Point
Wraps the existing Flask web app inside a native WebView window using pywebview.
Run: python desktop_app.py
"""
import threading
import time
import sys
import os
from pathlib import Path

# ── Path fix for PyInstaller .exe ─────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)        # temp extraction dir inside .exe
    WORK_DIR = Path(sys.executable).parent  # folder where .exe lives
else:
    BASE_DIR = Path(__file__).parent
    WORK_DIR = BASE_DIR

# Change cwd so aury.db and downloads/ are created next to the executable
os.chdir(WORK_DIR)

# Signal desktop mode so config.py picks the Windows download path
os.environ['AURY_DESKTOP'] = '1'

# ── Import Flask app AFTER chdir and env var set ──────────────────────────────
from web_server import app as flask_app, init_config

PORT = 5000


def start_flask():
    """Run Flask server on localhost only (desktop security — not exposed on LAN)."""
    init_config()
    flask_app.run(
        host='127.0.0.1',
        port=PORT,
        debug=False,
        use_reloader=False,
        threaded=True,
    )


def wait_for_server(timeout: int = 10) -> bool:
    """Poll until Flask is accepting connections or timeout expires."""
    import urllib.request
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{PORT}/', timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def main():
    try:
        import webview
    except ImportError:
        print("ERROR: pywebview is not installed.")
        print("Run: pip install pywebview")
        sys.exit(1)

    # Start Flask in a daemon thread
    flask_thread = threading.Thread(target=start_flask, daemon=True, name='flask')
    flask_thread.start()

    print("⏳  Starting AURY server…")
    if not wait_for_server(timeout=15):
        print("❌  Flask server failed to start within 15 seconds. Exiting.")
        sys.exit(1)

    print("✅  Server ready — opening window")

    # ── Create the native desktop window ─────────────────────────────────────
    window = webview.create_window(
        title='AURY — Smart Media Downloader',
        url=f'http://127.0.0.1:{PORT}/',
        width=1280,
        height=820,
        min_size=(900, 620),
        resizable=True,
        text_select=True,
        confirm_close=True,
        background_color='#1a1614',   # matches dark theme background
    )

    def on_closed():
        print("👋  AURY closed.")

    window.events.closed += on_closed

    # blocking — keeps the process alive until the window is closed
    webview.start(
        debug=False,
        private_mode=False,
        storage_path=str(WORK_DIR / '.webview_data'),
    )


if __name__ == '__main__':
    main()
