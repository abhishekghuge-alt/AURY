import os
import shutil
from pathlib import Path

# ─── App Info ────────────────────────────────────────────────────────────────
APP_NAME = "AURY"
APP_VERSION = "1.0"

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOAD_DIR = BASE_DIR / "downloads"
DATABASE_PATH = BASE_DIR / "aury.db"

# Local Temp Folder to avoid Google Drive file-locking
import tempfile
TEMP_DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "aury_temp"
TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Auto-create download subfolders on import
for _sub in ("video", "audio", "images", "documents", "archives", "others"):
    (DOWNLOAD_DIR / _sub).mkdir(parents=True, exist_ok=True)

# ─── Quality Map (keys 1-10; key 0 = audio-only, handled by UI) ──────────────
QUALITY_MAP: dict[str, tuple[str, str]] = {
    "1":  ("4K (2160p)",         "bestvideo[height<=2160]+bestaudio/best"),
    "2":  ("2K (1440p)",         "bestvideo[height<=1440][width>=2560]+bestaudio/best"
                                  "[width>=2560]/bestvideo[height<=1440]+bestaudio/best"),
    "3":  ("1440p",              "bestvideo[height<=1440]+bestaudio/best"),
    "4":  ("1080p (Recommended)","bestvideo[height<=1080]+bestaudio/best"),
    "5":  ("720p",               "bestvideo[height<=720]+bestaudio/best"),
    "6":  ("576p",               "bestvideo[height<=576]+bestaudio/best"),
    "7":  ("480p",               "bestvideo[height<=480]+bestaudio/best"),
    "8":  ("360p",               "bestvideo[height<=360]+bestaudio/best"),
    "9":  ("240p",               "bestvideo[height<=240]+bestaudio/best"),
    "10": ("144p",               "bestvideo[height<=144]+bestaudio/best"),
}

# ─── Rich color names ─────────────────────────────────────────────────────────
COLOR_PRIMARY   = "bright_cyan"
COLOR_SECONDARY = "bright_magenta"
COLOR_SUCCESS   = "bright_green"
COLOR_ERROR     = "bright_red"
COLOR_WARNING   = "bright_yellow"
COLOR_DIM       = "grey62"

# ─── Hex colors for GUI ───────────────────────────────────────────────────────
HEX_PRIMARY = "#00ffff"
HEX_SUCCESS = "#00ff00"
HEX_ERROR   = "#ff0000"
HEX_WARNING = "#ffff00"

CLI_BANNER_GRADIENT = ["cyan", "bright_cyan", "deep_sky_blue1", "sky_blue1"]

# ─── Performance & feature flags ─────────────────────────────────────────────
MAX_WORKERS              = 8
SPEED_LIMIT_BYTES        = 0      # 0 = unlimited
AUTO_OPEN_AFTER_DOWNLOAD = False
DEFAULT_QUALITY_KEY      = "4"
AUTO_START_ON_URL_PASTE  = False

# ─── aria2c Speed Boost ─────────────────────────────────────────────────────
HAS_ARIA2C = shutil.which("aria2c") is not None

# Priority list of browsers to check for cookies
BROWSER_LIST = ["chrome", "edge", "brave", "firefox", "opera", "vivaldi"]

def get_installed_browsers():
    """Returns a list of browsers that actually exist on this system."""
    import os
    local = os.environ.get('LOCALAPPDATA', '')
    roaming = os.environ.get('APPDATA', '')
    
    paths = {
        "chrome": os.path.join(local, "Google/Chrome/User Data"),
        "edge": os.path.join(local, "Microsoft/Edge/User Data"),
        "brave": os.path.join(local, "BraveSoftware/Brave-Browser/User Data"),
        "firefox": os.path.join(roaming, "Mozilla/Firefox/Profiles"),
        "opera": os.path.join(roaming, "Opera Software/Opera Stable"),
    }
    
    installed = []
    for name in BROWSER_LIST:
        path = paths.get(name)
        if path and os.path.exists(path):
            installed.append(name)
    return installed

INSTALLED_BROWSERS = get_installed_browsers()
# Default to the first one found, usually Chrome
COOKIES_BROWSER = INSTALLED_BROWSERS[0] if INSTALLED_BROWSERS else None



class _SilentLogger:
    def debug(self, msg):
        if msg.startswith("[debug]"):
            return
    def info(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg):
        # Only surface fatal errors, not cookie/DPAPI noise
        if any(skip in msg for skip in [
            "cookie", "DPAPI", "Chrome", "decrypt",
            "keyring", "Could not copy"
        ]):
            return
        # All other real errors: pass to Rich console
        from rich.console import Console
        Console().print(f"[bright_red]⚠ {msg}[/]")


def get_ydl_base_opts(quality_format: str) -> dict:
    """
    Return a yt-dlp options dict.
    NOTE: callers MUST set 'outtmpl' themselves — it is NOT set here
          because the destination subfolder depends on media type.
    """
    opts: dict = {
        "format":         quality_format,
        "quiet":          True,
        "no_warnings":    True,
        "noprogress":      True,         # we handle progress ourselves
        "windowsfilenames": True,       # sanitise filenames for Windows
        "concurrent_fragment_downloads": 16 if HAS_ARIA2C else 8,
        "buffer_size":    "16M",
        "buffersize":      1024 * 1024,
        "http_chunk_size": 10485760,
        "ignoreerrors":   "only_download",
        "logger":         _SilentLogger(),
    }

    if SPEED_LIMIT_BYTES > 0:
        opts["ratelimit"] = SPEED_LIMIT_BYTES

    # Audio-only → MP3 320 k via FFmpeg
    if quality_format == "bestaudio/best":
        opts["postprocessors"] = [{
            "key":              "FFmpegExtractAudio",
            "preferredcodec":   "mp3",
            "preferredquality": "320",
        }]

    return opts

def clean_url(raw: str) -> str:
    """
    Strip tracking parameters from YouTube and other URLs.
    KEEPS: v=, list=, index=, t=
    STRIPS: si=, utm_source=, utm_medium=, utm_campaign=, etc.
    """
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    
    # Handle youtu.be shortlinks (which don't have query params for the video ID)
    if "youtu.be/" in raw and "?" in raw:
        # e.g. https://youtu.be/abc123?si=xyz -> https://youtu.be/abc123
        base, query = raw.split("?", 1)
        # Keep 't' if present
        qs = parse_qs(query)
        if 't' in qs:
            return f"{base}?t={qs['t'][0]}"
        return base
    elif "youtu.be/" in raw:
        return raw

    # Handle standard URLs
    u = urlparse(raw)
    if not u.query:
        return raw
        
    qs = parse_qs(u.query)
    
    # Define whitelist
    whitelist = {'v', 'list', 'index', 't'}
    
    # Filter params
    new_qs = {k: v for k, v in qs.items() if k in whitelist}
    
    if not new_qs and not u.query:
        return raw
        
    # Rebuild
    new_query = urlencode(new_qs, doseq=True)
    return urlunparse(u._replace(query=new_query))
