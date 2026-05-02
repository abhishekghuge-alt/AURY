"""
AURY Web Server — Flask-based browser UI for the Smart Media Downloader.
Wraps core/downloader.py, core/database.py, and core/config.py.
"""

import json
import queue
import threading
import time
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from flask_cors import CORS

from core import config, database
from core.config import QUALITY_MAP, init_config
from core.downloader import DownloadWorker, pause_event, stop_event

app = Flask(__name__)
CORS(app)

# ── Global state ──────────────────────────────────────────────────────────────
_active_workers: dict[str, dict] = {}   # worker_key → {worker, title, progress, ...}
_sse_queues:     list[queue.Queue] = []  # broadcast channels for progress SSE
_lock = threading.Lock()

def _broadcast(event: str, data: dict):
    """Push an SSE event to every connected client."""
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_bytes(n: int) -> str:
    if n <= 0:      return "0 B"
    if n < 1024:    return f"{n} B"
    if n < 1 << 20: return f"{n/1024:.1f} KB"
    if n < 1 << 30: return f"{n/(1<<20):.1f} MB"
    return f"{n/(1<<30):.2f} GB"

def _fmt_speed(bps: float) -> str:
    if not bps:     return "—"
    if bps < 1024:  return f"{bps:.0f} B/s"
    if bps < 1<<20: return f"{bps/1024:.1f} KB/s"
    return f"{bps/(1<<20):.1f} MB/s"

def _fmt_eta(secs) -> str:
    if secs is None or secs < 0: return "—"
    secs = int(secs)
    if secs < 60:   return f"{secs}s"
    if secs < 3600: return f"{secs//60}m {secs%60:02d}s"
    return f"{secs//3600}h {(secs%3600)//60:02d}m"


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    db = database.get_db()
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
def api_history():
    db      = database.get_db()
    limit   = int(request.args.get("limit", 50))
    page    = int(request.args.get("page", 1))
    search  = request.args.get("q", "").strip()
    plat    = request.args.get("platform", "").strip()
    status  = request.args.get("status", "").strip()
    rows    = db.get_filtered_history(
        limit=limit, offset=(page - 1) * limit,
        search_term=search or None,
        platform_filter=plat or None,
        status_filter=status or None,
    )
    total   = db.get_history_count(
        search_term=search or None,
        platform_filter=plat or None,
        status_filter=status or None,
    )
    platforms = db.get_history_platforms()
    result = []
    for r in rows:
        d = dict(r)
        d["file_size_fmt"] = _fmt_bytes(d.get("file_size_bytes") or 0)
        result.append(d)
    return jsonify({"rows": result, "total": total, "platforms": platforms})


@app.route("/api/queue")
def api_queue():
    with _lock:
        items = []
        for key, w in _active_workers.items():
            items.append({
                "key":      key,
                "url":      w.get("url", ""),
                "title":    w.get("title", w.get("url", "")),
                "quality":  w.get("quality", ""),
                "status":   w.get("status", "downloading"),
                "progress": round(w.get("progress", 0), 1),
                "speed":    _fmt_speed(w.get("speed", 0)),
                "eta":      _fmt_eta(w.get("eta")),
                "size_fmt": _fmt_bytes(w.get("total_bytes", 0)),
            })
    return jsonify(items)


@app.route("/api/download", methods=["POST"])
def api_download():
    data    = request.get_json(force=True)
    url     = (data.get("url") or "").strip()
    quality = (data.get("quality") or config.DEFAULT_QUALITY_KEY).strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    # Map quality label → (label, format_string)
    q_key = quality
    # If the user sent a label like "1080p", find its key
    if quality not in QUALITY_MAP:
        for k, (lbl, _) in QUALITY_MAP.items():
            if quality.lower() in lbl.lower():
                q_key = k
                break
        else:
            q_key = config.DEFAULT_QUALITY_KEY

    quality_label, quality_format = QUALITY_MAP.get(q_key, QUALITY_MAP["4"])

    # Handle audio-only request
    audio_only = data.get("audio_only", False)
    if audio_only:
        quality_label  = "MP3 320kbps"
        quality_format = "bestaudio/best"

    db = database.get_db()
    session_id = db.get_last_session_id() or db.start_session()

    worker_key = f"{url[:40]}_{int(time.time())}"

    with _lock:
        _active_workers[worker_key] = {
            "url":         url,
            "title":       url,
            "quality":     quality_label,
            "status":      "starting",
            "progress":    0.0,
            "speed":       0.0,
            "eta":         None,
            "total_bytes": 0,
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
                w["speed"]       = payload.get("speed", 0.0)
                w["eta"]         = payload.get("eta")
                w["total_bytes"] = payload.get("total_bytes", 0)
            elif event == "complete":
                w["status"]   = "done"
                w["progress"] = 100.0
            elif event == "error":
                w["status"]   = "error"
        _broadcast("queue_update", {
            "key":      worker_key,
            "title":    _active_workers.get(worker_key, {}).get("title", url),
            "quality":  quality_label,
            "status":   _active_workers.get(worker_key, {}).get("status", ""),
            "progress": _active_workers.get(worker_key, {}).get("progress", 0),
            "speed":    _fmt_speed(_active_workers.get(worker_key, {}).get("speed", 0)),
            "eta":      _fmt_eta(_active_workers.get(worker_key, {}).get("eta")),
        })

    def _progress_cb(event: str, payload: dict):
        on_progress(event, payload)

    def run():
        try:
            worker = DownloadWorker(
                session_id    = session_id,
                url           = url,
                quality_label = quality_label,
                quality_format= quality_format,
                progress_callback=_progress_cb,
            )
            result = worker.run()
            with _lock:
                if worker_key in _active_workers:
                    _active_workers[worker_key]["status"] = (
                        "done" if result and result.status == "completed" else "error"
                    )
                    _active_workers[worker_key]["progress"] = 100.0
            _broadcast("queue_update", {
                "key":    worker_key,
                "status": _active_workers.get(worker_key, {}).get("status", "done"),
                "progress": 100.0,
            })
            # Auto-remove after 10s
            time.sleep(10)
            with _lock:
                _active_workers.pop(worker_key, None)
        except Exception as e:
            with _lock:
                if worker_key in _active_workers:
                    _active_workers[worker_key]["status"] = "error"
            _broadcast("queue_update", {"key": worker_key, "status": "error", "error": str(e)})

    t = threading.Thread(target=run, daemon=True)
    t.start()

    return jsonify({"ok": True, "key": worker_key, "quality": quality_label})


@app.route("/api/queue/<key>/stop", methods=["POST"])
def api_stop(key):
    stop_event.set()
    time.sleep(0.2)
    stop_event.clear()
    with _lock:
        if key in _active_workers:
            _active_workers[key]["status"] = "stopped"
    return jsonify({"ok": True})


@app.route("/api/analytics")
def api_analytics():
    db = database.get_db()
    return jsonify({
        "weekly":    db.get_analytics_weekly(),
        "activity":  db.get_analytics_activity_14d(),
        "quality":   db.get_analytics_quality_split(),
        "platform":  db.get_analytics_platform_split(),
    })


@app.route("/api/settings", methods=["GET"])
def api_settings_get():
    db = database.get_db()
    keys = ["download_dir", "default_quality", "max_workers", "audio_format",
            "turbo_mode", "auto_subtitles", "clip_watch", "theme"]
    out = {}
    for k in keys:
        out[k] = db.get_setting(k)
    out["quality_map"] = {k: v[0] for k, v in QUALITY_MAP.items()}
    return jsonify(out)


@app.route("/api/settings", methods=["POST"])
def api_settings_post():
    data = request.get_json(force=True)
    db   = database.get_db()
    for k, v in data.items():
        db.set_setting(k, str(v))
    init_config()
    return jsonify({"ok": True})


@app.route("/stream")
def stream():
    """SSE endpoint — pushes queue_update events to the browser."""
    q = queue.Queue(maxsize=100)
    with _lock:
        _sse_queues.append(q)

    def generate():
        # Send a heartbeat immediately so the connection is established
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
        headers={
            "Cache-Control":   "no-cache",
            "X-Accel-Buffering":"no",
        },
    )


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_config()
    print("🚀  AURY Web UI starting on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
