"""
Demo script: downloads a Michael Jackson song using AURY's core engine
and displays output just like the CLI would.
"""
import sys, time, threading
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from concurrent.futures import ThreadPoolExecutor, as_completed

from core import config, database, downloader
from cli import ui

console = Console()

URL = "https://www.dailymotion.com/video/x7tgad0"
QUALITY_LABEL = "720p"
QUALITY_FMT   = "bestvideo[height<=720]+bestaudio/best"

console.print(Panel.fit(
    "[bold bright_cyan]AURY Demo — Live Download (720p)[/]\n"
    f"[dim]URL:[/] {URL}\n"
    f"[dim]Quality:[/] {QUALITY_LABEL}\n"
    "[dim italic]Note: YouTube requires browser login cookies in server environments.[/]\n"
    "[dim italic]Using Dailymotion to demonstrate full AURY download flow.[/]",
    border_style="bright_cyan"
))

# Start a fresh session
session_id = database.db.start_session()

download_states: dict = {}
completion_times: dict = {}
display_rows: list = []
state_lock = threading.Lock()

def progress_cb(data: dict) -> None:
    dl_id = int(data.get("dl_id") or 0)
    if dl_id <= 0:
        return
    with state_lock:
        if dl_id not in download_states:
            display_rows.append(dl_id)
        download_states[dl_id] = data
        if data.get("status") in ("finished", "failed", "stopped"):
            completion_times[dl_id] = time.time()

def get_renderable():
    with state_lock:
        table = Table.grid(expand=True)
        table.add_column()
        now = time.time()
        to_remove = []
        for dl_id in list(display_rows):
            data = download_states.get(dl_id)
            if not data:
                continue
            if dl_id in completion_times:
                if now - completion_times[dl_id] > 2.0:
                    to_remove.append(dl_id)
                    continue
            table.add_row(ui.make_single_line_progress(data))
        for rid in to_remove:
            if rid in display_rows:
                display_rows.remove(rid)
        return table

downloader.stop_event.clear()
downloader.pause_event.set()

console.print(f"\n[bright_yellow]⬇  Starting download...[/]\n")

results = []
with Live(get_renderable(), refresh_per_second=10, transient=False) as live:
    with ThreadPoolExecutor(max_workers=1) as pool:
        w = downloader.DownloadWorker(
            session_id, URL, QUALITY_LABEL, QUALITY_FMT, progress_cb
        )
        futures = {pool.submit(w.run): w}
        for fut in as_completed(futures):
            result = fut.result()
            results.append(result)
            with state_lock:
                if result.id in download_states:
                    download_states[result.id]["status"] = result.status
                    completion_times[result.id] = time.time()

    start_wait = time.time()
    while display_rows and (time.time() - start_wait < 2.1):
        time.sleep(0.1)

database.db.end_session(session_id)

# Show results
for r in results:
    if r.status == "completed":
        size_mb = (r.file_size or 0) / (1024 * 1024)
        speed_mb = (r.speed_avg or 0) / (1024 * 1024)
        console.print(Panel(
            f"[bright_green]✔  Download complete![/]\n"
            f"[dim]Title:[/]   {r.title}\n"
            f"[dim]File:[/]    {r.file_path}\n"
            f"[dim]Size:[/]    {size_mb:.1f} MB\n"
            f"[dim]Speed:[/]   {speed_mb:.1f} MB/s",
            border_style="bright_green",
            title="Result"
        ))
    else:
        console.print(Panel(
            f"[bright_red]✘  Download failed[/]\n"
            f"[dim]Status:[/] {r.status}\n"
            f"[dim]Error:[/]  {getattr(r, 'error', 'unknown')}",
            border_style="bright_red",
            title="Result"
        ))

# Show session table
ui.show_session_table(session_id)
