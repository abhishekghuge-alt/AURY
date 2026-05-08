"""AURY Web Server v3 — Full 16-page browser UI for the Smart Media Downloader."""

import csv
import io
import json
import os
import queue
import secrets
import threading
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (Flask, Response, jsonify, render_template,
                   request, send_file, session, stream_with_context)
from flask_cors import CORS

from core import config, database
from core.config import QUALITY_MAP, init_config
from core.downloader import DownloadWorker, pause_event, stop_event

app = Flask(__name__)
app.secret_key = os.environ.get("AURY_SECRET", secrets.token_hex(32))
CORS(app)

# ── Global state ───────────────────────────────────────────────────────────────
_active_workers: dict[str, dict] = {}
_sse_queues:     list[queue.Queue] = []
_notifications:  list[dict] = []
_speed_history:  list[float] = []
_lock       = threading.Lock()
_notif_lock = threading.Lock()


# ── SSE broadcast ─────────────────────────────────────────────────────────────
def _broadcast(event: str, data: dict):
    msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
    with _lock:
        dead = []
        for q in _sse_queues:
            try:
                q.put_nowait(msg)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_queues.remove(q)


def _add_notification(kind: str, title: str, body: str = "") -> dict:
    entry = {
        "id":    int(time.time() * 1000),
        "kind":  kind,
        "title": title,
        "body":  body,
        "time":  datetime.now().strftime("%H:%M:%S"),
        "ts":    int(time.time()),
    }
    with _notif_lock:
        _notifications.insert(0, entry)
        if len(_notifications) > 300:
            _notifications.pop()
    _broadcast("notification", entry)
    return entry


# ── Formatters ────────────────────────────────────────────────────────────────
def _fmt_bytes(n):
    n = int(n or 0)
    if n <= 0:      return "0 B"
    if n < 1024:    return f"{n} B"
    if n < 1 << 20: return f"{n/1024:.1f} KB"
    if n < 1 << 30: return f"{n/(1<<20):.1f} MB"
    return f"{n/(1<<30):.2f} GB"

def _fmt_speed(bps):
    if not bps:     return "—"
    if bps < 1024:  return f"{bps:.0f} B/s"
    if bps < 1<<20: return f"{bps/1024:.1f} KB/s"
    return f"{bps/(1<<20):.1f} MB/s"

def _fmt_eta(secs):
    if secs is None or secs < 0: return "—"
    secs = int(secs)
    if secs < 60:   return f"{secs}s"
    if secs < 3600: return f"{secs//60}m {secs%60:02d}s"
    return f"{secs//3600}h {(secs%3600)//60:02d}m"


# ── Auth helpers ──────────────────────────────────────────────────────────────
def _auth_enabled() -> bool:
    return database.get_db().get_setting("auth_enabled", "0") == "1"

def _auth_ok() -> bool:
    if not _auth_enabled():
        return True
    return session.get("authenticated") is True

def _require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _auth_ok():
            return jsonify({"error": "Unauthorized"}), 401
        return fn(*args, **kwargs)
    return wrapper


# ── Core download logic ───────────────────────────────────────────────────────
def _start_download_thread(url: str, quality: str, subtitles=False, audio_only=False,
                           sub_langs=None, embed_subs=False, sub_only=False,
                           private=False) -> str:
    q_key = quality
    if quality not in QUALITY_MAP:
        for k, (lbl, _) in QUALITY_MAP.items():
            if quality.lower() in lbl.lower():
                q_key = k
                break
        else:
            q_key = config.DEFAULT_QUALITY_KEY

    quality_label, quality_format = QUALITY_MAP.get(q_key, QUALITY_MAP["4"])
    if audio_only:
        quality_label  = "MP3 320kbps"
        quality_format = "bestaudio/best"

    db         = database.get_db()
    session_id = db.get_last_session_id() or db.start_session()
    worker_key = f"{url[:40]}_{int(time.time()*1000)}"

    with _lock:
        _active_workers[worker_key] = {
            "url": url, "title": url, "quality": quality_label,
            "status": "starting", "progress": 0.0,
            "speed": 0.0, "eta": None, "total_bytes": 0,
            "start_time": time.time(),
        }

    def on_progress(event: str, payload: dict):
        with _lock:
            if worker_key not in _active_workers:
                return
            w = _active_workers[worker_key]
            if event == "title":
                w["title"] = payload.get("title", w["title"])
            elif event == "progress":
                w["status"]      = "downloading"
                w["progress"]    = payload.get("percent", 0.0)
                spd              = payload.get("speed", 0.0)
                w["speed"]       = spd
                w["eta"]         = payload.get("eta")
                w["total_bytes"] = payload.get("total_bytes", 0)
                with _notif_lock:
                    _speed_history.append(spd or 0)
                    if len(_speed_history) > 60:
                        _speed_history.pop(0)
            elif event == "complete":
                w["status"] = "done"; w["progress"] = 100.0
            elif event == "error":
                w["status"] = "error"
        w = _active_workers.get(worker_key, {})
        _broadcast("queue_update", {
            "key":       worker_key,
            "title":     w.get("title", url),
            "quality":   quality_label,
            "status":    w.get("status", ""),
            "progress":  w.get("progress", 0),
            "speed":     _fmt_speed(w.get("speed", 0)),
            "speed_raw": w.get("speed", 0),
            "eta":       _fmt_eta(w.get("eta")),
            "size_fmt":  _fmt_bytes(w.get("total_bytes", 0)),
        })

    def run():
        try:
            # Resolve subtitle languages
            _sub_langs = sub_langs or (['en'] if subtitles else None)
            worker = DownloadWorker(
                session_id=session_id, url=url,
                quality_label=quality_label, quality_format=quality_format,
                progress_callback=on_progress,
                sub_langs=_sub_langs,
                embed_subs=embed_subs,
                sub_only=sub_only,
            )
            result      = worker.run()
            final_status = "done" if result and result.status == "completed" else "error"
            with _lock:
                if worker_key in _active_workers:
                    _active_workers[worker_key]["status"]   = final_status
                    _active_workers[worker_key]["progress"] = 100.0
            _broadcast("queue_update", {"key": worker_key, "status": final_status, "progress": 100.0})
            title_s = _active_workers.get(worker_key, {}).get("title", url)[:60]
            if final_status == "done":
                _add_notification("success", "Download complete", title_s)
            else:
                _add_notification("error", "Download failed", title_s)
            time.sleep(10)
            with _lock:
                _active_workers.pop(worker_key, None)
            _broadcast("queue_update", {"key": worker_key, "status": "removed"})
        except Exception as e:
            with _lock:
                if worker_key in _active_workers:
                    _active_workers[worker_key]["status"] = "error"
            _broadcast("queue_update", {"key": worker_key, "status": "error", "error": str(e)})
            _add_notification("error", "Download error", str(e)[:80])

    threading.Thread(target=run, daemon=True).start()
    return worker_key


# ── Scheduler background thread ───────────────────────────────────────────────
def _scheduler_loop():
    while True:
        time.sleep(30)
        try:
            db      = database.get_db()
            pending = db.get_scheduled_pending()
            now_ts  = int(time.time())
            for item in pending:
                if item["scheduled_ts"] <= now_ts:
                    db.mark_scheduled_fired(item["id"])
                    _start_download_thread(item["url"], item["quality"])
                    _add_notification("info", "Scheduled download started", item["url"][:60])
        except Exception:
            pass

threading.Thread(target=_scheduler_loop, daemon=True).start()


# ── Preset queries for DB Report ──────────────────────────────────────────────
PRESET_QUERIES = [
    ("All downloads (full view)",     "SELECT * FROM v_downloads_full ORDER BY id DESC LIMIT 50"),
    ("Platform stats",                "SELECT * FROM v_platform_stats ORDER BY total_downloads DESC"),
    ("Daily activity (14 days)",      "SELECT * FROM v_daily_activity LIMIT 14"),
    ("Downloads by quality",          "SELECT quality_label, COUNT(*) AS count, SUM(file_size_bytes) AS bytes FROM downloads GROUP BY quality_label ORDER BY count DESC"),
    ("Failed downloads",              "SELECT id, title, url, last_error, downloaded_at FROM downloads WHERE status='failed' ORDER BY id DESC LIMIT 20"),
    ("Top 10 largest files",          "SELECT title, quality_label, file_size_bytes, downloaded_at FROM downloads WHERE status='completed' ORDER BY file_size_bytes DESC LIMIT 10"),
    ("Sessions summary",              "SELECT id, started_at, ended_at, total_files, completed_files, failed_files, total_bytes FROM sessions ORDER BY id DESC"),
    ("Tags and tagged downloads",     "SELECT t.name AS tag, COUNT(dt.download_id) AS count FROM tags t LEFT JOIN download_tags dt ON t.id=dt.tag_id GROUP BY t.id ORDER BY count DESC"),
]


# ── Routes — Core pages ───────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    db    = database.get_db()
    stats = db.get_stats()
    adv   = db.get_advanced_stats()
    return jsonify({
        "total_downloads": stats.get("total_downloads", 0),
        "total_sessions":  stats.get("total_sessions", 0),
        "total_bytes":     stats.get("total_bytes", 0),
        "total_bytes_fmt": _fmt_bytes(stats.get("total_bytes", 0)),
        "db_size_fmt":     _fmt_bytes(adv.get("db_size_bytes", 0)),
        "active_count":    len(_active_workers),
    })


@app.route("/api/history")
@_require_auth
def api_history():
    db     = database.get_db()
    limit  = int(request.args.get("limit", 50))
    page   = int(request.args.get("page", 1))
    search = request.args.get("q", "").strip()
    plat   = request.args.get("platform", "").strip()
    status = request.args.get("status", "").strip()
    tag    = request.args.get("tag", "").strip()
    rows   = db.get_filtered_history(
        limit=limit, offset=(page - 1) * limit,
        search=search or "",
        platform=plat or "All",
        status=status or "All",
    )
    total     = db.get_history_count(search=search or "", platform=plat or "All", status=status or "All")
    platforms = db.get_history_platforms()
    result = []
    for r in rows:
        d = dict(r)
        d["file_size_fmt"] = _fmt_bytes(d.get("file_size_bytes") or 0)
        d["speed_fmt"]     = _fmt_speed(d.get("avg_speed_bps") or 0)
        result.append(d)
    return jsonify({"rows": result, "total": total, "platforms": platforms})


@app.route("/api/history/<int:dl_id>", methods=["DELETE"])
@_require_auth
def api_history_delete(dl_id):
    database.get_db().delete_download(dl_id)
    return jsonify({"ok": True})


@app.route("/api/queue")
def api_queue():
    with _lock:
        items = []
        for key, w in _active_workers.items():
            items.append({
                "key":       key,
                "url":       w.get("url", ""),
                "title":     w.get("title", w.get("url", "")),
                "quality":   w.get("quality", ""),
                "status":    w.get("status", "downloading"),
                "progress":  round(w.get("progress", 0), 1),
                "speed":     _fmt_speed(w.get("speed", 0)),
                "speed_raw": w.get("speed", 0),
                "eta":       _fmt_eta(w.get("eta")),
                "size_fmt":  _fmt_bytes(w.get("total_bytes", 0)),
                "elapsed":   int(time.time() - w.get("start_time", time.time())),
            })
    return jsonify(items)


@app.route("/api/download", methods=["POST"])
@_require_auth
def api_download():
    data       = request.get_json(force=True)
    url        = (data.get("url") or "").strip()
    quality    = (data.get("quality") or config.DEFAULT_QUALITY_KEY).strip()
    audio_only = data.get("audio_only", False)
    subtitles  = data.get("subtitles", False)
    sub_langs  = data.get("sub_langs") or None       # list or None
    embed_subs = data.get("embed_subs", False)
    sub_only   = data.get("sub_only", False)
    private    = data.get("private", False)
    if not url:
        return jsonify({"error": "URL is required"}), 400
    key = _start_download_thread(
        url, quality,
        subtitles=subtitles, audio_only=audio_only,
        sub_langs=sub_langs, embed_subs=embed_subs,
        sub_only=sub_only, private=private,
    )
    _add_notification("info", "Download queued", url[:60])
    return jsonify({"ok": True, "key": key})


@app.route("/api/queue/<key>/stop", methods=["POST"])
@_require_auth
def api_stop(key):
    stop_event.set()
    time.sleep(0.2)
    stop_event.clear()
    with _lock:
        if key in _active_workers:
            _active_workers[key]["status"] = "stopped"
            _add_notification("warning", "Download stopped")
    return jsonify({"ok": True})


@app.route("/api/analytics")
def api_analytics():
    db = database.get_db()
    return jsonify({
        "weekly":        db.get_analytics_weekly(),
        "activity":      db.get_analytics_activity_14d(),
        "quality":       db.get_analytics_quality_split(),
        "platform":      db.get_analytics_platform_split(),
        "speed_history": list(_speed_history),
    })


@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    db   = database.get_db()
    keys = ["download_dir", "default_quality", "max_workers", "audio_format",
            "turbo_mode", "auto_subtitles", "clip_watch", "theme",
            "auth_enabled", "aria2c_mode",
            "private_dir", "private_enabled", "private_pin"]
    out = {}
    for k in keys:
        out[k] = db.get_setting(k)
    out["quality_map"] = {k: v[0] for k, v in QUALITY_MAP.items()}
    return jsonify(out)


@app.route("/api/settings", methods=["POST"])
@_require_auth
def api_settings_post():
    data = request.get_json(force=True)
    db   = database.get_db()
    for k, v in data.items():
        db.set_setting(k, str(v))
    # Update runtime download dir if changed
    if "download_dir" in data and data["download_dir"]:
        try:
            new_dir = Path(data["download_dir"])
            new_dir.mkdir(parents=True, exist_ok=True)
            config.DOWNLOAD_DIR = new_dir
            for _sub in ("video", "audio", "images", "documents", "archives", "others"):
                (new_dir / _sub).mkdir(parents=True, exist_ok=True)
        except Exception:
            pass  # Keep existing dir if path is invalid (e.g. Windows path on Linux)
    init_config()
    return jsonify({"ok": True})


# ── Auth ─────────────────────────────────────────────────────────────────────
@app.route("/api/auth/status")
def api_auth_status():
    return jsonify({"enabled": _auth_enabled(), "ok": _auth_ok()})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data   = request.get_json(force=True)
    pin    = str(data.get("pin", "")).strip()
    db     = database.get_db()
    stored = db.get_setting("auth_pin", "")
    if pin == stored:
        session["authenticated"] = True
        return jsonify({"ok": True})
    return jsonify({"error": "Wrong PIN"}), 401


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.pop("authenticated", None)
    return jsonify({"ok": True})


@app.route("/api/auth/set-pin", methods=["POST"])
@_require_auth
def api_auth_set_pin():
    data = request.get_json(force=True)
    pin  = str(data.get("pin", "")).strip()
    db   = database.get_db()
    db.set_setting("auth_pin", pin)
    db.set_setting("auth_enabled", "1" if pin else "0")
    return jsonify({"ok": True})


# ── URL Info (thumbnail, title, size) ────────────────────────────────────────
@app.route("/api/info")
def api_info():
    url = (request.args.get("url") or "").strip()
    if not url:
        return jsonify({"error": "No URL"}), 400
    result = {"url": url, "title": None, "thumbnail": None, "duration": None,
              "filesize": None, "filesize_fmt": None, "platform": None}
    try:
        import yt_dlp
        ydl_opts = {"quiet": True, "no_warnings": True,
                    "socket_timeout": 8, "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        result["title"]     = info.get("title")
        result["thumbnail"] = info.get("thumbnail")
        result["duration"]  = info.get("duration")
        result["platform"]  = info.get("extractor_key", "Unknown")
        result["uploader"]  = info.get("uploader")
        fmts = info.get("formats") or []
        best = max(fmts, key=lambda f: f.get("filesize") or 0, default=None)
        if best and best.get("filesize"):
            result["filesize"]     = best["filesize"]
            result["filesize_fmt"] = _fmt_bytes(best["filesize"])
    except Exception as e:
        result["error"] = str(e)[:150]
    return jsonify(result)


# ── Batch Download ────────────────────────────────────────────────────────────
@app.route("/api/batch", methods=["POST"])
@_require_auth
def api_batch():
    data    = request.get_json(force=True)
    urls    = [u.strip() for u in (data.get("urls") or []) if u.strip()]
    quality = (data.get("quality") or config.DEFAULT_QUALITY_KEY).strip()
    audio   = data.get("audio_only", False)
    if not urls:
        return jsonify({"error": "No URLs provided"}), 400
    keys = [_start_download_thread(u, quality, audio_only=audio) for u in urls[:50]]
    _add_notification("info", f"Batch queued: {len(keys)} downloads")
    return jsonify({"ok": True, "keys": keys, "count": len(keys)})


# ── Scheduler ─────────────────────────────────────────────────────────────────
@app.route("/api/scheduler", methods=["GET"])
@_require_auth
def api_scheduler_get():
    return jsonify(database.get_db().get_scheduled_items())


@app.route("/api/scheduler", methods=["POST"])
@_require_auth
def api_scheduler_post():
    data     = request.get_json(force=True)
    url      = (data.get("url") or "").strip()
    quality  = (data.get("quality") or config.DEFAULT_QUALITY_KEY).strip()
    when_str = (data.get("when") or "").strip()
    repeat   = (data.get("repeat") or "none").strip()
    note     = (data.get("note") or "").strip()
    if not url or not when_str:
        return jsonify({"error": "URL and schedule time required"}), 400
    try:
        ts = int(datetime.fromisoformat(when_str).timestamp())
    except Exception:
        return jsonify({"error": "Invalid datetime format"}), 400
    item_id = database.get_db().add_scheduled(url=url, quality=quality,
                                              scheduled_ts=ts, repeat=repeat, note=note)
    _add_notification("info", "Download scheduled", f"{url[:40]} @ {when_str}")
    return jsonify({"ok": True, "id": item_id})


@app.route("/api/scheduler/<int:item_id>", methods=["DELETE"])
@_require_auth
def api_scheduler_delete(item_id):
    database.get_db().delete_scheduled(item_id)
    return jsonify({"ok": True})


# ── Tags ─────────────────────────────────────────────────────────────────────
@app.route("/api/tags", methods=["GET"])
def api_tags_get():
    return jsonify(database.get_db().get_all_tags())


@app.route("/api/tags", methods=["POST"])
@_require_auth
def api_tags_post():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip().lower()
    if not name:
        return jsonify({"error": "Tag name required"}), 400
    tid = database.get_db().create_tag(name)
    return jsonify({"ok": True, "id": tid, "name": name})


@app.route("/api/tags/<int:tag_id>", methods=["DELETE"])
@_require_auth
def api_tags_delete(tag_id):
    database.get_db().delete_tag(tag_id)
    return jsonify({"ok": True})


@app.route("/api/downloads/<int:dl_id>/tags", methods=["GET"])
def api_dl_tags_get(dl_id):
    return jsonify(database.get_db().get_download_tags(dl_id))


@app.route("/api/downloads/<int:dl_id>/tags", methods=["POST"])
@_require_auth
def api_dl_tags_add(dl_id):
    data   = request.get_json(force=True)
    tag_id = int(data.get("tag_id", 0))
    database.get_db().add_download_tag(dl_id, tag_id)
    return jsonify({"ok": True})


@app.route("/api/downloads/<int:dl_id>/tags/<int:tag_id>", methods=["DELETE"])
@_require_auth
def api_dl_tags_remove(dl_id, tag_id):
    database.get_db().remove_download_tag(dl_id, tag_id)
    return jsonify({"ok": True})


# ── File Manager ──────────────────────────────────────────────────────────────
@app.route("/api/files")
@_require_auth
def api_files():
    dl_dir = Path(config.DOWNLOAD_DIR)
    folder = request.args.get("folder", "")  # Optional subfolder (video, audio, etc.)
    
    if folder:
        target_dir = dl_dir / folder
        # Security: ensure folder is within DOWNLOAD_DIR
        try:
            target_dir = target_dir.resolve()
            if not str(target_dir).startswith(str(dl_dir.resolve())):
                return jsonify({"error": "Invalid folder path"}), 400
        except Exception:
            return jsonify({"error": "Invalid folder path"}), 400
    else:
        target_dir = dl_dir
    
    if not target_dir.exists():
        return jsonify({"files": [], "folders": [], "path": str(target_dir), "count": 0, "total_bytes": 0})
    
    files = []
    folders = []
    total_bytes = 0
    
    # List subfolders first
    for item in sorted(target_dir.iterdir(), key=lambda x: x.name.lower()):
        if item.is_dir():
            folders.append({
                "name": item.name,
                "path": item.name if not folder else f"{folder}/{item.name}",
            })
    
    # List files
    for f in sorted(target_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file():
            stat = f.stat()
            total_bytes += stat.st_size
            files.append({
                "name":        f.name,
                "size":        stat.st_size,
                "size_fmt":    _fmt_bytes(stat.st_size),
                "ext":         f.suffix.lower(),
                "modified":    datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                "modified_ts": int(stat.st_mtime),
                "folder":      folder,
            })
    
    return jsonify({
        "files": files,
        "folders": folders,
        "path": str(target_dir),
        "current_folder": folder,
        "count": len(files),
        "total_bytes_fmt": _fmt_bytes(total_bytes)
    })


@app.route("/api/files/<path:filename>")
@_require_auth
def api_file_download(filename):
    dl_dir = Path(config.DOWNLOAD_DIR)
    # Support folder prefix in filename (e.g., "video/file.mp4")
    fp = (dl_dir / filename).resolve()
    if not fp.exists() or not str(fp).startswith(str(dl_dir.resolve())):
        return jsonify({"error": "File not found"}), 404
    return send_file(fp, as_attachment=True)


@app.route("/api/files/<path:filename>", methods=["DELETE"])
@_require_auth
def api_file_delete(filename):
    dl_dir = Path(config.DOWNLOAD_DIR)
    # Support folder prefix in filename (e.g., "video/file.mp4")
    fp = (dl_dir / filename).resolve()
    try:
        if not str(fp).startswith(str(dl_dir.resolve())):
            return jsonify({"error": "Invalid file path"}), 400
        fp.unlink(missing_ok=True)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── DB Report ─────────────────────────────────────────────────────────────────
@app.route("/api/db-query", methods=["POST"])
@_require_auth
def api_db_query():
    data = request.get_json(force=True)
    sql  = (data.get("sql") or "").strip()
    if not sql:
        return jsonify({"error": "No SQL provided"}), 400
    try:
        rows = database.get_db().run_safe_query(sql)
        cols = list(rows[0].keys()) if rows else []
        return jsonify({"ok": True, "rows": rows, "columns": cols, "count": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/db-presets")
def api_db_presets():
    return jsonify([{"label": lbl, "sql": sql} for lbl, sql in PRESET_QUERIES])


# ── Notifications ─────────────────────────────────────────────────────────────
@app.route("/api/notifications")
def api_notifications():
    with _notif_lock:
        return jsonify(list(_notifications))


@app.route("/api/notifications", methods=["DELETE"])
def api_notifications_clear():
    with _notif_lock:
        _notifications.clear()
    return jsonify({"ok": True})


# ── Platform stats ────────────────────────────────────────────────────────────
@app.route("/api/platform-stats")
def api_platform_stats():
    db = database.get_db()
    with db._lock:
        cursor = db.conn.execute("""
            SELECT p.name, p.icon, p.domain,
                   COUNT(d.id) AS total,
                   SUM(CASE WHEN d.status='completed' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN d.status='failed'    THEN 1 ELSE 0 END) AS failed,
                   SUM(d.file_size_bytes)  AS total_bytes,
                   AVG(d.avg_speed_bps)   AS avg_speed
            FROM platforms p
            LEFT JOIN downloads d ON d.platform_id = p.id
            GROUP BY p.id ORDER BY total DESC
        """)
        rows = [dict(r) for r in cursor.fetchall()]
    for r in rows:
        r["total_bytes_fmt"] = _fmt_bytes(r["total_bytes"] or 0)
        r["avg_speed_fmt"]   = _fmt_speed(r["avg_speed"] or 0)
    return jsonify(rows)


# ── Export / Backup ───────────────────────────────────────────────────────────
@app.route("/api/export/csv")
@_require_auth
def api_export_csv():
    db   = database.get_db()
    rows = db.get_filtered_history(limit=10000)
    si   = io.StringIO()
    cols = ["id", "title", "url", "platform", "quality_label", "status",
            "file_size_bytes", "duration_secs", "downloaded_at", "file_path"]
    w = csv.DictWriter(si, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    out = io.BytesIO(si.getvalue().encode())
    return send_file(out, mimetype="text/csv", as_attachment=True,
                     download_name="aury_downloads.csv")


@app.route("/api/export/db")
@_require_auth
def api_export_db():
    from core.config import DATABASE_PATH
    return send_file(DATABASE_PATH, as_attachment=True, download_name="aury.db")


# ── SSE stream ────────────────────────────────────────────────────────────────
@app.route("/stream")
def stream():
    q = queue.Queue(maxsize=100)
    with _lock:
        _sse_queues.append(q)

    def generate():
        yield ": heartbeat\n\n"
        try:
            while True:
                try:
                    msg = q.get(timeout=20)
                    yield msg
                except queue.Empty:
                    yield ": heartbeat\n\n"
        except GeneratorExit:
            pass
        finally:
            with _lock:
                try:
                    _sse_queues.remove(q)
                except ValueError:
                    pass

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_config()
    print("🚀  AURY Web UI v3 starting on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
