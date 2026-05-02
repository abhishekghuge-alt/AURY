"""
cli/main.py — AURY V1 CLI entry point.
Orchestrates the 9-step download flow described in the spec.
All UI output goes through cli.ui — zero print() calls here.
"""

import shutil
import socket
import sys
import threading
import time
import os
import platform
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

from core import config, database, downloader
from cli import ui, settings

# Set by main() after startup checks
FFMPEG_AVAILABLE: bool = True


# ─── Startup checks ──────────────────────────────────────────────────────────

def _check_internet() -> bool:
    """Checks for internet by trying multiple reliable hosts."""
    targets = [
        ("8.8.8.8", 53),      # Google DNS
        ("1.1.1.1", 53),      # Cloudflare DNS
        ("google.com", 80),   # HTTP Google
        ("bing.com", 80)      # HTTP Microsoft
    ]
    for host, port in targets:
        try:
            socket.create_connection((host, port), timeout=3)
            return True
        except OSError:
            continue
    return False


# ─── Keyboard hotkeys (P / R / S) ────────────────────────────────────────────

def _listen_hotkeys(stop_listener: threading.Event) -> None:
    """
    Runs in a daemon thread during active downloads.
    Requires the 'keyboard' package — silently degrades if missing.
    """
    try:
        import keyboard
    except Exception:
        ui.show_keyboard_missing_hint()
        return

    paused = False
    while not stop_listener.is_set() and not downloader.stop_event.is_set():
        if keyboard.is_pressed("p"):
            if not paused:
                downloader.pause_event.clear()
                paused = True
                ui.show_paused()
            else:
                downloader.pause_event.set()
                paused = False
                ui.show_resumed()
            time.sleep(0.3)
        if keyboard.is_pressed("s"):
            if ui.prompt_stop_confirm():
                downloader.stop_event.set()
                downloader.pause_event.set()  # unblock any paused threads
                ui.show_stopping()
                break
            time.sleep(0.3)
        time.sleep(0.05)


# ─── Build download queue ─────────────────────────────────────────────────────

def _build_queue(urls: list[str]) -> list[tuple[str, str, str, int]]:
    """
    STEP 2 + STEP 3:
    Ask quality scope, ask quality per URL if needed,
    check for duplicates, return filtered queue.

    Returns list of (url, url_original, quality_label, quality_format, is_redownload).
    """
    scope = ui.prompt_quality_scope()

    raw_queue: list[tuple[str, str, str, str]] = []
    if scope == "a":
        q_label, q_fmt = ui.prompt_quality("all videos")
        raw_queue = [(url, orig, q_label, q_fmt) for url, orig in urls]
    else:
        for url, orig in urls:
            q_label, q_fmt = ui.prompt_quality(url[:60])
            raw_queue.append((url, orig, q_label, q_fmt))

    filtered: list[tuple[str, str, str, str, int]] = []
    for url, orig, label, fmt in raw_queue:
        # If ffmpeg missing, strip audio stream from combined format
        if not FFMPEG_AVAILABLE and "+" in fmt:
            fmt = fmt.split("+", 1)[0]

        when = database.db.check_duplicate(url)
        if not when:
            filtered.append((url, orig, label, fmt, 0))
        elif ui.prompt_redownload(url, when):
            filtered.append((url, orig, label, fmt, 1))
        # else: user said "n" — skip silently

    return filtered


# ─── Run one batch of downloads ───────────────────────────────────────────────

def _run_download_batch(
    session_id: int,
    queue_items: list[tuple[str, str, str, str, int]],
    sub_langs: list[str] = None,
    sub_only: bool = False,
    embed_subs: bool = False,
    is_quick_mode: bool = False
) -> list:
    """
    STEP 4 + STEP 5:
    Show start message, spin up workers, display live progress bars.
    Returns list[DownloadResult].
    """
    from rich.live import Live
    from rich.console import Group
    from rich.table import Table

    ui.show_start_message(len(queue_items), config.MAX_WORKERS)

    # State management for progress display
    download_states: dict[int, dict] = {}   # dl_id -> latest progress data
    completion_times: dict[int, float] = {} # dl_id -> time when finished
    display_rows: list[int] = []            # dl_id order for display
    state_lock = threading.Lock()

    def progress_cb(data: dict) -> None:
        dl_id = int(data.get("dl_id") or 0)
        if dl_id <= 0: return
        
        with state_lock:
            if dl_id not in download_states:
                display_rows.append(dl_id)
            download_states[dl_id] = data
            
            if data.get("status") in ("finished", "failed", "stopped"):
                completion_times[dl_id] = time.time()

    # Reset control events for this batch
    downloader.stop_event.clear()
    downloader.pause_event.set()

    stop_listener = threading.Event()
    hotkey_thread = threading.Thread(
        target=_listen_hotkeys, args=(stop_listener,), daemon=True
    )
    hotkey_thread.start()

    results = []
    
    # Custom renderable function for Live
    def get_renderable():
        with state_lock:
            # 1. Progress Table (invisible borders for clean look)
            table = Table.grid(expand=True)
            table.add_column()
            
            now = time.time()
            to_remove = []
            
            for dl_id in list(display_rows):
                data = download_states.get(dl_id)
                if not data: continue
                
                # Handle completion fade-out (2 seconds)
                if dl_id in completion_times:
                    if now - completion_times[dl_id] > 2.0:
                        to_remove.append(dl_id)
                        continue
                
                table.add_row(ui.make_single_line_progress(data))
            
            for rid in to_remove:
                if rid in display_rows: display_rows.remove(rid)
                
            return table

    with Live(get_renderable(), refresh_per_second=10, transient=False) as live:
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as pool:
            workers = []
            for url, orig, label, fmt, redownload in queue_items:
                w = downloader.DownloadWorker(
                    session_id, url, label, fmt, progress_cb,
                    sub_langs=sub_langs, sub_only=sub_only, embed_subs=embed_subs,
                    is_quick_mode=is_quick_mode
                )
                w._url_original = orig # Assign original URL
                w._forced_redownload = redownload
                workers.append(w)

            futures = {pool.submit(w.run): w for w in workers}

            for fut in as_completed(futures):
                result = fut.result()
                results.append(result)
                
                # Ensure the final state is captured
                with state_lock:
                    if result.id in download_states:
                        download_states[result.id]["status"] = result.status
                        if result.status == "failed":
                            download_states[result.id]["speed"] = 0
                            download_states[result.id]["eta"] = None
                        completion_times[result.id] = time.time()

        # Wait for any remaining "finished" items to fade out (max 2s)
        start_wait = time.time()
        while display_rows and (time.time() - start_wait < 2.1):
            time.sleep(0.1)

    stop_listener.set()   # tell hotkey thread to stop
    return results


# ─── FEATURE 2: Scheduling logic ──────────────────────────────────────────────

def _wait_for_schedule(target_time: datetime, urls_count: int, quality_label: str) -> bool:
    """Shows a live countdown until target_time. Returns True if reached, False if cancelled."""
    from rich.live import Live
    import keyboard

    def get_renderable():
        now = datetime.now()
        rem = target_time - now
        if rem.total_seconds() <= 0:
            return ui.Panel("Starting now...", border_style="success")
        
        # Calculate progress bar for time
        # We don't have a start time for the countdown itself easily, so just show remaining
        rem_str = str(rem).split('.')[0] # HH:MM:SS
        
        return ui.Panel(
            f"{urls_count} URLs queued · Quality: {quality_label}\n"
            f"Starting at: {target_time.strftime('%H:%M:%S')}\n"
            f"Time remaining: [primary]{rem_str}[/]\n\n"
            f"[C] Cancel schedule",
            title="⏳ Scheduled Download",
            border_style="primary"
        )

    with Live(get_renderable(), refresh_per_second=1, transient=True) as live:
        while datetime.now() < target_time:
            if keyboard.is_pressed("c"):
                return False
            time.sleep(0.5)
            live.update(get_renderable())
    
    return True


# ─── Single session (Steps 1-8) ───────────────────────────────────────────────

def _run_single_session() -> None:
    """
    Opens a DB session, runs the full URL → quality → download → report loop.
    Steps 1-8. Step 9 (continue/exit) is handled by main().
    """
    # STEP 1
    urls = ui.prompt_urls()

    # STEP 2 + 3
    queue = _build_queue(urls)
    if not queue:
        ui.show_no_urls_to_download()
        return

    # FEATURE 1: Subtitles
    sub_choice = ui.prompt_subtitle_options()
    sub_langs = None
    sub_only = False
    embed_subs = False
    if sub_choice in (1, 2):
        sub_langs = ui.prompt_subtitle_language()
        if sub_choice == 1:
            embed_subs = True
        else:
            sub_only = True

    # FEATURE 2: Scheduling
    sched_choice = ui.prompt_schedule_options()
    target_dt = None
    if sched_choice == 2:
        mins = ui.prompt_schedule_delay()
        target_dt = datetime.now() + timedelta(minutes=mins)
    elif sched_choice == 3:
        time_str = ui.prompt_schedule_time()
        now = datetime.now()
        target_dt = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        if target_dt < now:
            # Assume tomorrow if time is in the past
            target_dt += timedelta(days=1)

    if target_dt:
        q_label = queue[0][1] if queue else "Mixed"
        if not _wait_for_schedule(target_dt, len(queue), q_label):
            if ui.show_schedule_cancelled():
                return
            else:
                sys.exit(0)

    session_id = database.db.start_session(scheduled_time=target_dt.isoformat() if target_dt else None)
    try:
        # STEP 4 + 5 — download; STEP 8 — retry loop
        results = _run_download_batch(session_id, queue, sub_langs, sub_only, embed_subs)

        while True:
            # STEP 6
            ui.show_session_table(session_id)

            # STEP 7
            ui.prompt_export_csv(session_id)

            # STEP 8
            failed = [r for r in results if r.status == "failed"]
            if not failed:
                break
                
            choice = ui.prompt_post_session_retry(len(failed))
            if choice == "n":
                break
            elif choice == "s":
                queue_path = os.path.join(config.BASE_DIR, "retry_queue.txt")
                with open(queue_path, "a", encoding="utf-8") as f:
                    for r in failed:
                        f.write(r.url + "\n")
                ui.console.print(f"  ✔ Saved {len(failed)} URLs to retry_queue.txt")
                break
            elif choice == "y":
                # Re-queue only failed URLs with same quality
                retry_queue = [
                    (r.url, r.quality_label, r.quality_format, 1)
                    for r in failed
                ]
                results = _run_download_batch(session_id, retry_queue, sub_langs, sub_only, embed_subs)

    finally:
        database.db.end_session(session_id)


# ─── FEATURE 4: Quick Download ───────────────────────────────────────────────

def _run_quick_download(prefilled_urls: list[str] = None) -> None:
    if prefilled_urls:
        # Wrap in tuples (cleaned, original)
        urls = [(config.clean_url(u), u) for u in prefilled_urls]
    else:
        urls = ui.prompt_urls(is_quick=True)
        
    if not urls:
        ui.show_no_urls_to_download()
        return

    # Use default quality from settings, fallback to 1080p
    default_q = database.db.get_setting("default_quality", "4")
    if default_q not in config.QUALITY_MAP:
        default_q = "4"
    q_label, q_fmt = config.QUALITY_MAP[default_q]

    # Quick download skips duplicate check UI, we just download it anyway (is_redownload=0)
    queue = [(url, orig, q_label, q_fmt, 0) for url, orig in urls]

    session_id = database.db.start_session()
    try:
        _run_download_batch(
            session_id, 
            queue, 
            sub_langs=None, 
            sub_only=False, 
            embed_subs=False,
            is_quick_mode=True
        )
        ui.show_session_table(session_id)
    finally:
        database.db.end_session(session_id)


# ─── FEATURE 3: History logic ────────────────────────────────────────────────

def _run_history() -> None:
    search = ""
    platform = "All"
    status = "All"
    sort = "Newest"
    offset = 0
    limit = 15
    
    while True:
        rows = database.db.get_filtered_history(search, platform, status, sort, limit, offset)
        total = database.db.get_history_count(search, platform, status)
        
        ui.show_history_table(rows, total, offset, limit, search, platform, status, sort)
        
        action = ui.prompt_history_action()
        if not action or action in ("B", "BACK", "EXIT", "X", "Q"):
            break
            
        if action == "N": # Next
            if offset + limit < total:
                offset += limit
            continue
        if action == "P": # Prev
            if offset - limit >= 0:
                offset -= limit
            continue
            
        if action == "S": # Search
            search = ui.prompt_history_search()
            offset = 0
            continue
            
        if action == "F": # Filter Platform
            platforms = ["All"] + database.db.get_history_platforms()
            # Simple cyclic filter for now or a prompt
            p_idx = platforms.index(platform)
            platform = platforms[(p_idx + 1) % len(platforms)]
            offset = 0
            continue

        if action == "T": # Filter Status (using T for status to avoid conflict with S/Search)
            statuses = ["All", "Completed", "Failed", "Pending"]
            s_idx = statuses.index(status)
            status = statuses[(s_idx + 1) % len(statuses)]
            offset = 0
            continue
            
        if action == "O": # Sort
            sorts = ["Newest", "Oldest", "Largest", "Fastest"]
            o_idx = sorts.index(sort)
            sort = sorts[(o_idx + 1) % len(sorts)]
            offset = 0
            continue

        if action == "E": # Export CSV
            all_history = database.db.get_filtered_history(search, platform, status, sort, limit=1000)
            if all_history:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_path = config.DOWNLOAD_DIR / f"history_export_{ts}.csv"
                import csv
                with open(out_path, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=all_history[0].keys())
                    writer.writeheader()
                    writer.writerows(all_history)
                ui.console.print(f"[success]✔ Exported {len(all_history)} records to {out_path}[/]")
            continue

        if action == "C": # Clear all
            if ui.prompt_clear_history_confirm():
                database.db.clear_all_history()
                offset = 0
            continue

        if action == "R": # Retry All Failed
            failed = database.db.get_filtered_history(status="Failed", limit=100)
            if failed:
                ui.console.print(f"  🔄 Re-queueing {len(failed)} failed downloads...")
                # Re-run logic similar to retry loop
                session_id = database.db.start_session()
                # (url, url_original, quality_label, quality_format, is_redownload)
                retry_queue = [(r["url"], r["url_original"], r["quality_label"], "best", 1) for r in failed]
                _run_download_batch(session_id, retry_queue)
                database.db.end_session(session_id)
            continue

        # Handle row # (Open file) or D# (Delete) or R# (Retry specific)
        try:
            if action.startswith("D") and action[1:].isdigit():
                row_idx = int(action[1:]) - 1
                local_idx = row_idx - offset
                if 0 <= local_idx < len(rows):
                    row = rows[local_idx]
                    if ui.console.input(f"Delete '{row['title'][:30]}...'? (y/n) → ").lower() == 'y':
                        database.db.delete_download(row["id"])
                continue

            if action.isdigit():
                row_idx = int(action) - 1
                local_idx = row_idx - offset
                if 0 <= local_idx < len(rows):
                    row = rows[local_idx]
                    path = row.get("file_path")
                    if path and os.path.exists(path):
                        if platform.system() == "Windows": os.startfile(path)
                        else: 
                            import subprocess
                            cmd = "open" if platform.system() == "Darwin" else "xdg-open"
                            subprocess.run([cmd, path])
                    else:
                        ui.show_file_missing(path or "Unknown")
                continue
        except Exception as e:
            ui.show_error_panel("Action Error", str(e))


# ─── Entry point ─────────────────────────────────────────────────────────────

def main() -> None:
    global FFMPEG_AVAILABLE

    # Init DB first (safe to call multiple times)
    # DB is initialized on module import

    # Start clipboard watcher
    from core.clipboard_watcher import ClipboardWatcher
    clipboard_watcher = ClipboardWatcher(ui.show_clipboard_notification)
    clipboard_watcher.start()

    # STEP 0 — banner
    ui.show_banner()

    # STEP 0 — internet check
    if not _check_internet():
        ui.show_no_internet_and_exit()
        sys.exit(1)

    # STEP 0 — ffmpeg check
    FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None
    if not FFMPEG_AVAILABLE:
        ui.show_ffmpeg_warning()

    try:
        # STEP 9 outer loop — "Download more?" restarts here
        while True:
            choice = ui.prompt_main_menu()
            if choice == "1":
                _run_single_session()
            elif choice == "2" or choice == "q":
                recent_url = clipboard_watcher.get_recent_url(window_seconds=5)
                if recent_url:
                    # Clipboard detection: skip all prompts including URL input
                    _run_quick_download(prefilled_urls=[recent_url])
                else:
                    _run_quick_download()
            elif choice == "3":
                _run_history()
            elif choice == "4":
                settings.run_settings()
            elif choice == "5":
                break

    except KeyboardInterrupt:
        downloader.stop_event.set()
        downloader.pause_event.set()
        ui.show_interrupted()
        sys.exit(0)

    # STEP 9 — goodbye using last completed session
    last_sid = database.db.get_last_session_id()
    if last_sid:
        ui.show_goodbye(last_sid)


if __name__ == "__main__":
    main()
