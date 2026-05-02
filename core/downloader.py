import os
import sys
import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

from core import database, config
from core.config import DOWNLOAD_DIR, TEMP_DOWNLOAD_DIR, get_ydl_base_opts

# ─── Global control events (singletons shared by CLI and GUI) ────────────────
pause_event = threading.Event()
pause_event.set()   # "set" = NOT paused
stop_event  = threading.Event()

# ─── File-type sorting buckets ───────────────────────────────────────────────
VIDEO_EXTS   = {"mp4", "mkv", "webm", "avi", "mov", "flv", "m4v", "ts"}
AUDIO_EXTS   = {"mp3", "m4a", "aac", "flac", "wav", "ogg", "opus", "wma"}
IMAGE_EXTS   = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg"}
DOC_EXTS     = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt", "epub"}
ARCHIVE_EXTS = {"zip", "rar", "7z", "tar", "gz", "bz2"}


@dataclass
class DownloadResult:
    id:             int
    url:            str
    status:         str          # "completed" | "failed" | "stopped"
    quality_label:  str
    quality_format: str
    file_path:      str   = ""
    file_size:      int   = 0
    duration:       float = 0.0
    error:          str   = ""
    speed_avg:      float = 0.0
    title:          str   = "Unknown"


class DownloadWorker:
    """One worker per URL. Runs on a background thread."""

    def __init__(self, session_id: int, url: str,
                 quality_label: str, quality_format: str,
                 progress_callback=None,
                 sub_langs: list[str] = None,
                 sub_only: bool = False,
                 embed_subs: bool = False,
                 is_quick_mode: bool = False):
        self.session_id      = session_id
        self.url             = url
        self.quality_label   = quality_label
        self.quality_format  = quality_format
        self.progress_callback = progress_callback
        self.sub_langs       = sub_langs
        self.sub_only        = sub_only
        self.embed_subs      = embed_subs
        self.is_quick_mode   = is_quick_mode

        self.dl_id:            int | None = None
        self._title:           str        = url
        self._forced_redownload            = None
        self._url_original:    str        = url
        self._started:         float      = time.time()
        self._last_speed:      float      = 0.0
        self._last_update:     float      = 0.0
        self._final_filepath:  str        = ""   # set by postprocessor hook

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _sort_destination(file_path: str) -> Path:
        """Move file into downloads/<type>/ subfolder.
        Reads config.DOWNLOAD_DIR at call time so runtime changes take effect."""
        src = Path(file_path)
        ext = src.suffix.lower().lstrip(".")
        dl_dir = config.DOWNLOAD_DIR          # runtime lookup, not import-time constant
        if ext in VIDEO_EXTS:
            folder = dl_dir / "video"
        elif ext in AUDIO_EXTS:
            folder = dl_dir / "audio"
        elif ext in IMAGE_EXTS:
            folder = dl_dir / "images"
        elif ext in DOC_EXTS:
            folder = dl_dir / "documents"
        elif ext in ARCHIVE_EXTS:
            folder = dl_dir / "archives"
        else:
            folder = dl_dir / "others"
        folder.mkdir(parents=True, exist_ok=True)
        return folder / src.name

    # ── Hooks ────────────────────────────────────────────────────────────────

    def _safe_name(self, name: str) -> str:
        """Truncate and clean filename for safe terminal display."""
        if not name: return "Unknown"
        # Remove extension if present in title
        name = name.rsplit('.', 1)[0] if '.' in name else name
        # Truncate to 50 chars and add ellipsis if needed
        if len(name) > 50:
            name = name[:47] + "..."
        return name

    def _progress_hook(self, payload: dict) -> None:
        """Called by yt-dlp on every chunk. Raises to abort on stop."""
        if stop_event.is_set():
            raise yt_dlp.utils.DownloadError("Stopped by user")

        # Honour pause
        while not pause_event.is_set():
            if stop_event.is_set():
                raise yt_dlp.utils.DownloadError("Stopped by user")
            time.sleep(0.25)

        # Throttle updates to 10/sec (100ms gate)
        now = time.monotonic()
        
        status = payload.get("status")
        
        # We always want to process "finished" or "error" immediately
        if status not in ("finished", "error"):
            if now - self._last_update < 0.1:
                return
        
        self._last_update = now

        if status == "downloading":
            self._last_speed = float(payload.get("speed") or 0.0)
            downloaded = int(payload.get("downloaded_bytes") or 0)
            total = int(payload.get("total_bytes") or payload.get("total_bytes_estimate") or 0)
            
            if self.progress_callback:
                self.progress_callback({
                    "dl_id":            self.dl_id,
                    "url":              self.url,
                    "status":           "downloading",
                    "downloaded_bytes": downloaded,
                    "total_bytes":      total,
                    "speed":            self._last_speed,
                    "eta":              payload.get("eta"),
                    "filename":         self._safe_name(self._title),
                    "sub_langs":        self.sub_langs,
                })
        elif status == "finished":
            if self.progress_callback:
                self.progress_callback({
                    "dl_id":    self.dl_id,
                    "url":      self.url,
                    "status":   "finished",
                    "filename": self._safe_name(self._title),
                    # Send final stats for the "finished" line
                    "downloaded_bytes": int(payload.get("total_bytes") or payload.get("downloaded_bytes") or 0),
                    "total_bytes":      int(payload.get("total_bytes") or payload.get("downloaded_bytes") or 0),
                    "speed":            self._last_speed,
                    "eta":              0,
                })

    def _pp_hook(self, d: dict) -> None:
        """Postprocessor hook — captures the FINAL output filepath (after conversion)."""
        if d.get("status") == "finished":
            fp = (d.get("info_dict") or {}).get("filepath") or d.get("filepath") or ""
            if fp:
                self._final_filepath = fp

    # ── Main entry point ─────────────────────────────────────────────────────

    def run(self) -> DownloadResult:
        # FIX 5 — Thread priority (Windows)
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.kernel32.SetThreadPriority(ctypes.windll.kernel32.GetCurrentThread(), 1)
            except Exception: pass

        if stop_event.is_set():
            return DownloadResult(0, self.url, "stopped",
                                  self.quality_label, self.quality_format)

        is_redownload = (
            self._forced_redownload
            if self._forced_redownload in (0, 1)
            else 0
        )
        sub_str = ",".join(self.sub_langs) if self.sub_langs else None
        self.dl_id = database.db.insert_download({
            "session_id": self.session_id,
            "url": self.url,
            "url_original": self._url_original,
            "quality_label": self.quality_label,
            "quality_format": self.quality_format,
            "is_redownload": is_redownload,
            "subtitles_lang": sub_str,
            "status": "downloading",
            "is_quick_mode": self.is_quick_mode
        })

        # yt-dlp options — download to LOCAL TEMP first to avoid Google Drive sync locks
        try:
            opts = get_ydl_base_opts(self.quality_format)
            # Use filename only for outtmpl, paths handle the directory
            opts["outtmpl"]            = "%(title).120s [%(id)s].%(ext)s"
            opts["paths"]              = {
                "home": str(TEMP_DOWNLOAD_DIR),
                "temp": str(TEMP_DOWNLOAD_DIR)
            }
            opts["progress_hooks"]     = [self._progress_hook]
            opts["postprocessor_hooks"] = [self._pp_hook]
            
            # aria2c turbo mode
            if shutil.which("aria2c"):
                turbo_setting = database.db.get_setting("aria2c_turbo", "auto")
                if turbo_setting != "off":
                    opts["external_downloader"] = "aria2c"
                    opts["external_downloader_args"] = {
                        "aria2c": [
                            "-x", "16",
                            "-s", "16",
                            "-k", "1M",
                            "--min-split-size=1M",
                            "--quiet",
                        ]
                    }

            # Subtitle Options
            if self.sub_langs:
                opts["writesubtitles"]     = True
                opts["writeautomaticsub"]  = True
                opts["subtitleslangs"]     = self.sub_langs
                opts["subtitlesformat"]    = "srt/vtt"
                if self.embed_subs:
                    opts["embedsubtitles"] = True
                if self.sub_only:
                    opts["skip_download"]  = True

            # --- Retry Engine & Cookie Fallback Logic ---
            from core.config import INSTALLED_BROWSERS
            browsers_to_try = list(INSTALLED_BROWSERS) if INSTALLED_BROWSERS else [None]
            
            last_error = ""
            success = False
            info = None
            
            max_retries = 3
            
            for attempt in range(max_retries + 1):
                if success or stop_event.is_set():
                    break

                for browser in browsers_to_try:
                    current_opts = dict(opts)
                    if browser:
                        current_opts["cookiesfrombrowser"] = (browser,)
                    else:
                        current_opts.pop("cookiesfrombrowser", None)

                    try:
                        with yt_dlp.YoutubeDL(current_opts) as ydl:
                            info = ydl.extract_info(self.url, download=False)
                            if not info: continue
                            
                            if info.get("_type") == "playlist":
                                entries = list(info.get("entries") or [])
                                if not entries: raise yt_dlp.utils.DownloadError("Playlist empty")

                            self._title = str(info.get("title") or self.url)
                            database.db.update_download_title(self.dl_id, self._title)
                            ydl.download([self.url])
                            success = True
                            break
                    except yt_dlp.utils.DownloadError as exc:
                        last_error = str(exc)
                        if "Could not copy" in last_error or "cookie" in last_error.lower():
                            continue
                        else: break 
                    except Exception as exc:
                        last_error = str(exc)
                        break

                if not success and attempt < max_retries and not stop_event.is_set():
                    # HTTP 403 (Forbidden) or 404 (Not Found): Permanent fail
                    if any(code in last_error for code in ["403", "404", "Forbidden"]):
                        break 

                    # HTTP 429 (Too Many Requests): Wait 30s
                    if "429" in last_error:
                        wait_time = 30
                    else:
                        # Exponential backoff: 5s, 10s, 20s
                        wait_time = 5 * (2 ** attempt)
                    
                    database.db.log_error(self.dl_id, last_error)
                    database.db.increment_retry(self.dl_id)

                    if self.progress_callback:
                        for w in range(wait_time, 0, -1):
                            if stop_event.is_set(): break
                            self.progress_callback({
                                "dl_id": self.dl_id,
                                "url": self.url,
                                "status": "retrying",
                                "filename": self._safe_name(self._title),
                                "attempt": attempt + 1,
                                "max_retries": max_retries,
                                "wait": w,
                                "error": last_error,
                            })
                            time.sleep(1)

            if not success:
                # Append to retry_queue.txt if failed
                queue_path = os.path.join(config.BASE_DIR, "retry_queue.txt")
                with open(queue_path, "a", encoding="utf-8") as f:
                    f.write(self._url_original + "\n")
                raise yt_dlp.utils.DownloadError(f"All {max_retries} retries failed. Saved to retry queue.")

            # ── Step 3: find the actual saved file in TEMP_DOWNLOAD_DIR ───
            file_path = self._final_filepath
            if not file_path:
                vid_id    = info.get("id", "")
                # Search in temp folder instead of DOWNLOAD_DIR
                predicted = TEMP_DOWNLOAD_DIR / f"{self._title[:120]} [{vid_id}]"
                for ext in ("mp4", "mkv", "webm", "mp3", "m4a"):
                    candidate = predicted.with_suffix(f".{ext}")
                    if candidate.exists():
                        file_path = str(candidate)
                        break
            
            # If still not found, try any file with the title in temp
            if not file_path:
                for f in TEMP_DOWNLOAD_DIR.iterdir():
                    if self._safe_name(self._title) in f.name:
                        file_path = str(f)
                        break

            # ── Step 4: sort into type subfolder ─────────────────────────
            if file_path and os.path.exists(file_path):
                dst = self._sort_destination(file_path)
                
                # Move associated subtitle files if they exist
                src_path = Path(file_path)
                for sub_ext in (".srt", ".vtt", ".ass"):
                    sub_file = src_path.with_suffix(sub_ext)
                    if sub_file.exists():
                        sub_dst = dst.with_suffix(sub_ext)
                        if sub_dst.exists():
                            sub_dst = sub_dst.with_name(f"{sub_dst.stem}_{int(time.time())}{sub_ext}")
                        shutil.move(str(sub_file), str(sub_dst))

                if Path(file_path).resolve() != dst.resolve():
                    if dst.exists():
                        stem   = dst.stem
                        suffix = dst.suffix
                        dst    = dst.with_name(f"{stem}_{int(time.time())}{suffix}")
                    shutil.move(file_path, dst)
                    file_path = str(dst)

            file_size = os.path.getsize(file_path) if (file_path and os.path.exists(file_path)) else 0
            duration  = time.time() - self._started
            speed_avg = (file_size / duration) if (duration > 0 and file_size > 0) else self._last_speed

            database.db.update_status(
                self.dl_id, 
                "completed", 
                file_size_bytes=file_size, 
                file_path=file_path, 
                duration_secs=duration,
                avg_speed_bps=speed_avg
            )
            return DownloadResult(
                self.dl_id, self.url, "completed",
                self.quality_label, self.quality_format,
                file_path  = file_path,
                file_size  = file_size,
                duration   = duration,
                speed_avg  = speed_avg,
                title      = self._title,
            )

        except yt_dlp.utils.DownloadError as exc:
            msg = str(exc)
            if "Stopped by user" in msg or stop_event.is_set():
                database.db.update_status(self.dl_id, "stopped")
                status = "stopped"
            else:
                database.db.log_error(self.dl_id, msg)
                database.db.update_status(self.dl_id, "failed")
                status = "failed"
            return DownloadResult(
                self.dl_id or 0, self.url, status,
                self.quality_label, self.quality_format,
                error=msg, title=self._title,
            )
