"""
cli/ui.py — ALL Rich terminal output for AURY V1 CLI.
Every screen, prompt, and styled panel is defined here.
main.py never calls print() — only functions from this module.
"""

import csv
import os
from datetime import datetime
from pathlib import Path

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from core import config, database

# ─── Themed console ──────────────────────────────────────────────────────────
aury_theme = Theme({
    "primary":   config.COLOR_PRIMARY,
    "secondary": config.COLOR_SECONDARY,
    "success":   config.COLOR_SUCCESS,
    "error":     config.COLOR_ERROR,
    "warning":   config.COLOR_WARNING,
    "dim":       config.COLOR_DIM,
})
console = Console(theme=aury_theme)


# ─── Internal helpers ────────────────────────────────────────────────────────

def _fmt_bytes(num: int) -> str:
    if not num or num <= 0:
        return "0.0 MB"
    return f"{num / (1024 ** 2):.1f} MB"


def _fmt_secs(secs: float) -> str:
    return f"{float(secs):.1f}s"


# ─── STEP 0: Banner ──────────────────────────────────────────────────────────

def show_banner() -> None:
    stats = database.db.get_stats()
    total_gb = (stats["total_bytes"] or 0) / (1024 ** 3)

    art = Text(
        "\n".join([
            "██████╗  ██╗   ██╗ ██████╗  ██╗   ██╗",
            "██╔═══██╗ ██║   ██║ ██╔══██╗ ╚██╗ ██╔╝",
            "███████║  ██║   ██║ ██████╔╝  ╚████╔╝ ",
            "██╔══██║  ██║   ██║ ██╔══██╗   ╚██╔╝  ",
            "██║  ██║  ╚██████╔╝ ██║  ██║    ██║   ",
            "╚═╝  ╚═╝   ╚═════╝  ╚═╝  ╚═╝    ╚═╝   ",
        ]),
        style="primary",
    )
    console.print(Panel(
        Align.center(art),
        subtitle="Smart Media Downloader | V1 CLI",
        border_style="primary",
    ))
    console.print(
        f"📦 Lifetime: {stats['total_downloads']} downloads · "
        f"{total_gb:.2f} GB · {stats['total_sessions']} sessions"
    )

    import shutil
    has_aria2c = shutil.which("aria2c") is not None
    if has_aria2c:
        console.print("⚡ aria2c detected → Turbo mode ON (16x connections)", style="primary")
    else:
        console.print("💡 Install aria2c for 3x faster downloads", style="dim")


def show_ffmpeg_warning() -> None:
    console.print(Panel(
        "⚠  ffmpeg not found on PATH.\n"
        "   Video+audio merge disabled. Install ffmpeg for best quality.",
        border_style="warning",
    ))


def show_no_internet_and_exit() -> None:
    show_error_panel(
        "✘  No Internet Connection.",
        "Cannot reach network. Check your connection and try again.",
    )


# ─── STEP 1: URL input ───────────────────────────────────────────────────────

def prompt_urls(is_quick: bool = False) -> list[tuple[str, str]]:
    """Prompt for URLs. If multiple are pasted, or a .txt file is provided, show a preview."""
    while True:
        raw = console.input(
            "▶ Enter URL(s) or path to .txt file:\n  → "
        ).strip()

        if not raw:
            continue

        valid = []
        original_map = {} # cleaned -> original

        # Check if it's a .txt file
        if raw.lower().endswith(".txt") and os.path.exists(raw):
            try:
                with open(raw, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip().startswith("http")]
                    for l in lines:
                        cleaned = config.clean_url(l)
                        valid.append(cleaned)
                        original_map[cleaned] = l
            except Exception as e:
                show_error_panel("✘ Error reading file", str(e))
                continue
        else:
            # Split on commas and newlines
            chunks = [p.strip() for x in raw.splitlines() for p in x.split(",") if p.strip()]
            for u in chunks:
                if u.startswith("http://") or u.startswith("https://"):
                    cleaned = config.clean_url(u)
                    valid.append(cleaned)
                    original_map[cleaned] = u

        if not valid:
            show_error_panel(
                "✘  No valid URLs found.",
                "Each URL must start with http:// or https://"
            )
            continue
            
        # Preview panel
        if len(valid) > 0:
            title = f"📋 Detected {len(valid)} URLs"
            if raw.lower().endswith(".txt"):
                title += f" from {os.path.basename(raw)}"
            
            console.print(Panel(title, border_style="primary"))
            for i, u in enumerate(valid[:10], 1):
                orig = original_map.get(u, u)
                if u != orig:
                    console.print(f"  {i}. [success]🔧 Cleaned:[/] {u[:60]}{'...' if len(u)>60 else ''}")
                else:
                    console.print(f"  {i}. {u[:60]}{'...' if len(u)>60 else ''}")
            
            if len(valid) > 10:
                console.print(f"  ... and {len(valid) - 10} more.")
                
            if is_quick:
                return [(u, original_map[u]) for u in valid]

            ans = console.input("\n  Confirm queue? (y/n) [Enter=y] → ").strip().lower()
            if ans == "" or ans in ("y", "yes"):
                # We return the original URLs but main.py should handle cleaning or we return a map
                # Actually, the prompt says "url column = cleaned URL, url_original = what user pasted"
                # So we return the CLEANED urls, but we need a way to pass the originals to main.py
                # Let's return a list of dicts or tuples
                return [(u, original_map[u]) for u in valid]
            else:
                continue

def show_clipboard_notification(url: str, was_cleaned: bool = False) -> None:
    """Displays a floating notification about a new clipboard URL."""
    # Use ANSI to move up if we want, but simple print is safer and robust
    msg = f"📋 New URL copied!  {url[:50]}{'...' if len(url)>50 else ''}"
    if was_cleaned:
        msg += "\n🔧 Cleaned tracking params!"
        
    console.print(Panel(
        f"{msg}\nPress Q to Quick Download it",
        border_style="success",
        width=70
    ))


def prompt_redownload(url: str, when: str) -> bool:
    """Warn user that URL was already downloaded; ask whether to re-download."""
    prompt_time = when.replace("T", " ")[:16]   # e.g. "2026-04-28 14:32"
    while True:
        answer = console.input(
            f"  ⚠  '{url}' was already downloaded on {prompt_time}\n"
            f"     Re-download? (y/n) → "
        ).strip().lower()
        if answer in ("y", "yes"):
            return True
        elif answer in ("n", "no", ""):
            return False
        else:
            console.print("[bright_yellow]  Please enter y or n[/]")


# ─── STEP 2: Quality scope ───────────────────────────────────────────────────

def prompt_quality_scope() -> str:
    """Ask whether to apply one quality to all URLs or pick per URL."""
    console.print(Panel(
        "Apply quality to:\n"
        "[A] All videos  ←  same quality for all\n"
        "[I] Individual  ←  pick per video",
        border_style="dim",
    ))
    while True:
        choice = console.input("▶ Enter a or i → ").strip().lower()
        if choice in {"a", "i"}:
            return choice


# ─── STEP 3: Quality selection ───────────────────────────────────────────────

def prompt_quality(target: str, return_index=False):
    """
    Print the quality table and return (label, yt-dlp format string).
    Option 0 = Audio-only MP3 320k (handled here, not in QUALITY_MAP).
    Option 4 = 1080p is highlighted cyan as recommended.
    """
    table = Table(show_header=True, border_style="dim", expand=False)
    table.add_column("#",       justify="right", style="dim")
    table.add_column("Quality", min_width=24)
    table.add_column("Format",  min_width=40, style="dim")

    # Row 0 — audio only
    table.add_row("0", "🎵 Audio only (MP3 320k)", "bestaudio/best")

    # Rows 1-10 from QUALITY_MAP
    for key in map(str, range(1, 11)):
        label, fmt = config.QUALITY_MAP[key]
        if key == "4":
            # Highlight recommended
            table.add_row(
                f"[primary]{key}[/]",
                f"[primary]{label}  ← recommended[/]",
                f"[primary]{fmt}[/]",
            )
        else:
            table.add_row(key, label, fmt)

    console.print(table)

    while True:
        choice = console.input(f"▶ Quality for {target} (0–10) → ").strip()
        if choice == "0":
            return ("0", "Audio only (MP3 320k)", "bestaudio/best") if return_index else ("Audio only (MP3 320k)", "bestaudio/best")
        if choice in config.QUALITY_MAP:
            return (choice, *config.QUALITY_MAP[choice]) if return_index else config.QUALITY_MAP[choice]
        show_error_panel("✘ Invalid choice.", "Enter a number 0–10.")


# ─── FEATURE 1: Subtitles ──────────────────────────────────────────────────

def prompt_subtitle_options() -> int:
    """
    [1] Download subtitles with video
    [2] Subtitles only (no video)
    [3] Skip subtitles
    """
    console.print(Panel(
        "📝 Subtitle Options\n\n"
        "[1] Download subtitles with video\n"
        "[2] Subtitles only (no video)\n"
        "[3] Skip subtitles",
        border_style="primary",
    ))
    while True:
        choice = console.input("▶ Enter 1, 2, or 3 → ").strip()
        if choice in ("1", "2", "3"):
            return int(choice)


def prompt_subtitle_language() -> list[str]:
    """
    [1] English (en)
    [2] Hindi (hi)
    [3] Auto-detect (all available)
    [4] Enter language code manually
    """
    console.print(Panel(
        "🌐 Select Subtitle Language\n"
        "[1] English (en)\n"
        "[2] Hindi (hi)\n"
        "[3] Auto-detect (all available)\n"
        "[4] Enter language code manually",
        border_style="primary",
    ))
    while True:
        choice = console.input("▶ Enter 1–4 → ").strip()
        if choice == "1":
            return ["en"]
        elif choice == "2":
            return ["hi"]
        elif choice == "3":
            return ["all"]
        elif choice == "4":
            code = console.input("▶ Enter language code (e.g. en, hi, ja, fr) → ").strip().lower()
            if code:
                return [code]


# ─── STEP 4: Download start ──────────────────────────────────────────────────

def show_start_message(count: int, workers: int) -> None:
    console.print(f"\n🚀 Starting {count} download(s) with {workers} parallel workers…")


# ─── FEATURE 2: Scheduling ──────────────────────────────────────────────────

def prompt_schedule_options() -> int:
    """
    [1] Start NOW
    [2] Start after delay (minutes)
    [3] Start at exact time (HH:MM)
    """
    console.print(Panel(
        "⏰ Schedule Download?\n\n"
        "[1] Start NOW\n"
        "[2] Start after delay (minutes)\n"
        "[3] Start at exact time (HH:MM)",
        border_style="primary",
    ))
    while True:
        choice = console.input("▶ Enter 1, 2, or 3 → ").strip()
        if choice in ("1", "2", "3"):
            return int(choice)


def prompt_schedule_delay() -> int:
    while True:
        try:
            val = int(console.input("▶ Start after how many minutes? → ").strip())
            if val >= 0:
                return val
        except ValueError:
            pass
        console.print("[error]  Please enter a valid number of minutes.[/]")


def prompt_schedule_time() -> str:
    while True:
        val = console.input("▶ Enter start time (24hr format HH:MM) → ").strip()
        try:
            datetime.strptime(val, "%H:%M")
            return val
        except ValueError:
            console.print("[error]  Invalid format. Use HH:MM (e.g. 23:00)[/]")


def show_keyboard_missing_hint() -> None:
    console.print(
        "  ℹ  Install 'keyboard' for p/r/s hotkeys."
    )




# ─── STEP 5: Progress ────────────────────────────────────────────────────────

def make_single_line_progress(data: dict) -> Text:
    """
    Creates a single-line Text renderable for a download.
    [icon] [filename] [bar] [pct] [speed] [eta] [size]
    """
    status = data.get("status", "downloading")
    title  = data.get("filename", "Unknown")
    dl     = float(data.get("downloaded_bytes") or 0)
    total  = float(data.get("total_bytes") or 0)
    speed  = float(data.get("speed") or 0)
    eta    = data.get("eta")
    
    # 1. Icon
    icon_map = {
        "downloading": ("⬇", "primary"),
        "finished":    ("✔", "success"),
        "failed":      ("✘", "error"),
        "stopped":     ("⏹", "warning"),
        "paused":      ("⏸", "warning"),
        "retrying":    ("🔄", "warning"),
    }
    icon, style = icon_map.get(status, ("⬇", "primary"))
    
    # 2. Filename (fixed 50 chars)
    name_str = f"{title:<50}"
    
    if status == "retrying":
        att = data.get("attempt", 1)
        mx = data.get("max_retries", 3)
        wait = data.get("wait", 0)
        
        line = Text()
        line.append(f"{icon}  ", style=style)
        line.append(f"{name_str}  ", style="bright_white")
        
        retry_str = f"Retry {att}/{mx} in {wait}s..."
        line.append(f"{retry_str:<35}", style="warning")
        return line

    # 3. Progress Bar (fixed 25 chars)
    pct = dl / total if total > 0 else 0
    if pct > 1.0: pct = 1.0
    filled = int(25 * pct)
    empty  = 25 - filled
    bar_str = "━" * filled + "░" * empty
    bar_style = "success" if status == "finished" else "error" if status == "failed" else "primary"
    
    # 4. Speed (MB/s)
    speed_mb = speed / (1024 * 1024)
    speed_str = f"{speed_mb:>5.1f} MB/s"
    
    # 5. ETA (HH:MM:SS)
    if status == "finished":
        eta_str = "0:00:00"
    elif eta is None:
        eta_str = "-:--:--"
    else:
        import datetime
        eta_str = str(datetime.timedelta(seconds=int(eta)))
    eta_str = f"{eta_str:>8}"
    
    # 6. Size (2.0/2.0 MB)
    dl_mb    = dl / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    size_str = f"{dl_mb:>5.1f}/{total_mb:<5.1f} MB"

    # 7. Subtitles tag
    sub_langs = data.get("sub_langs")
    sub_tag = ""
    if sub_langs:
        sub_tag = f" +[📝 subs: {','.join(sub_langs)}]"

    # Assemble
    line = Text()
    line.append(f"{icon}  ", style=style)
    line.append(f"{name_str}  ", style="bright_white")
    line.append(f"{bar_str}  ", style=bar_style)
    line.append(f"{int(pct*100):>3}%  ", style="primary")
    line.append(f"{speed_str}  ", style="secondary")
    line.append(f"{eta_str}  ", style="dim")
    line.append(f"{size_str}", style="dim")
    if sub_tag:
        line.append(sub_tag, style="primary")

    return line


def make_progress() -> Progress:
    return Progress(
        SpinnerColumn(spinner_name="dots12"),
        TextColumn("[bold primary]{task.fields[status_icon]}[/]"),
        TextColumn("[bright_white]{task.fields[filename]:.45}[/]"),
        BarColumn(bar_width=22, style="primary", complete_style="success"),
        TaskProgressColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        DownloadColumn(),
        console=console,
        expand=True,
    )


def show_paused() -> None:
    console.print("  ⏸ Downloads PAUSED — press R to resume.")


def show_resumed() -> None:
    console.print("  ▶ Downloads RESUMED.")


def show_stopping() -> None:
    console.print("  ⏹ Stopping all downloads...")


def prompt_stop_confirm() -> bool:
    while True:
        answer = console.input(
            "  ⚠  This will stop ALL active downloads immediately.\n"
            "     Confirm stop? (y/n) → "
        ).strip().lower()
        if answer in ("y", "yes"):
            return True
        elif answer in ("n", "no", ""):
            return False
        else:
            console.print("[bright_yellow]  Please enter y or n[/]")


# ─── STEP 6: Session report ──────────────────────────────────────────────────

def show_session_table(session_id: int) -> None:
    rows = database.db.get_session_downloads(session_id)
    if not rows:
        return

    console.print("\n📋 Session Report")

    table = Table(expand=True, border_style="dim")
    table.add_column("#",        justify="right", width=3)
    table.add_column("Title",    min_width=28, max_width=32)
    table.add_column("Quality",  min_width=7)
    table.add_column("Status",   min_width=11)
    table.add_column("Subtitles", min_width=10)
    table.add_column("Size",     justify="right", min_width=8)
    table.add_column("Duration", justify="right", min_width=7)
    table.add_column("Saved To", min_width=22)

    for idx, row in enumerate(rows, 1):
        status = row.get("status", "")
        status_styled = {
            "completed": "[success]✔ completed[/]",
            "failed":    "[error]✘ failed[/]",
            "stopped":   "[warning]⏹ stopped[/]",
        }.get(status, status)

        fp    = str(row.get("file_path") or "—")
        # Show relative path if inside DOWNLOAD_DIR
        try:
            fp_rel = str(Path(fp).relative_to(config.DOWNLOAD_DIR))
        except ValueError:
            fp_rel = fp

        subs = str(row.get("subtitles_lang") or "—")
        if subs != "—":
            subs = f"✔ {subs}.srt"

        q_label = str(row.get("quality_label") or "—")
        if row.get("is_quick_mode"):
            q_label = "[primary]⚡ Quick[/]"

        table.add_row(
            str(idx),
            str(row.get("title") or "Unknown")[:30],
            q_label,
            status_styled,
            subs,
            _fmt_bytes(int(row.get("file_size_bytes") or 0)),
            _fmt_secs(float(row.get("duration_secs") or 0.0)),
            fp_rel[:26],
        )

    console.print(table)

    # Summary panel
    summary = database.db.get_session_summary(session_id)
    console.print(Panel(
        f"Session Summary\n"
        f"✔ {summary['completed']} completed   "
        f"✘ {summary['failed']} failed   "
        f"⏹ {summary['stopped']} stopped\n"
        f"📦 Total: {_fmt_bytes(summary['total_bytes'])}   "
        f"⏱ {summary['total_duration']:.1f}s",
        border_style="dim",
    ))


# ─── STEP 7: CSV export ───────────────────────────────────────────────────────

def prompt_export_csv(session_id: int) -> None:
    while True:
        answer = console.input("Export session to CSV? (y/n) → ").strip().lower()
        if answer in ("y", "yes"):
            break
        elif answer in ("n", "no", ""):
            return
        else:
            console.print("[bright_yellow]  Please enter y or n[/]")

    rows = database.db.get_session_downloads(session_id)
    if not rows:
        console.print("  ℹ No data to export.")
        return
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(config.DOWNLOAD_DIR) / f"session_{session_id}_{ts}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    console.print(f"  ✔ Exported to {out_path}")


# ─── STEP 8: Retry ───────────────────────────────────────────────────────────

def prompt_post_session_retry(count: int) -> str:
    console.print(Panel(
        f" {count} download(s) failed. Retry now?\n"
        " [Y] Yes   [N] Skip   [S] Save\n"
        " S = save URL to retry_queue.txt",
        border_style="warning"
    ))
    while True:
        choice = console.input("▶ Enter Y, N, or S → ").strip().lower()
        if choice in ("y", "n", "s"):
            return choice
        console.print("[bright_yellow]  Please enter Y, N, or S[/]")


# ─── STEP 9: Continue / exit ─────────────────────────────────────────────────

def prompt_continue() -> bool:
    while True:
        answer = (
            console.input("▶ Download more files? (y/n) → ")
            .strip().lower()
        )
        if answer in ("y", "yes"):
            return True
        elif answer in ("n", "no", ""):
            return False
        else:
            console.print("[bright_yellow]  Please enter y or n[/]")


def show_goodbye(session_id: int) -> None:
    summary = database.db.get_session_summary(session_id)
    console.print(Panel(
        "👋 Thanks for using AURY!\n"
        "Session complete.\n"
        f"✔ {summary['completed']} downloaded  "
        f"✘ {summary['failed']} failed  "
        f"📦 {_fmt_bytes(summary['total_bytes'])}  "
        f"⏱ {summary['total_duration']:.1f}s",
        border_style="primary",
    ))


# ─── Edge-case helpers ────────────────────────────────────────────────────────

def show_no_urls_to_download() -> None:
    console.print("  ℹ No URLs to download. Returning to main menu.")


def show_error_panel(title: str, message: str) -> None:
    console.print(Panel(message, title=title, border_style="error"))


def show_interrupted() -> None:
    console.print("\n  ⏹ Interrupted. Exiting AURY…")


# ─── FEATURE 3 & 6: Main Menu & History ───────────────────────────────────────

def prompt_main_menu() -> str:
    console.print(Panel(
        "AURY — Main Menu\n\n"
        "[1]  ⬇  Start New Download\n"
        "[2]  ⚡  Quick Download\n"
        "[3]  📋  View Download History\n"
        "[4]  ⚙  Settings\n"
        "[5]  ❌  Exit",
        border_style="primary",
    ))
    while True:
        choice = console.input("▶ Enter 1-5 or Q for Quick Download → ").strip().lower()
        if choice in ("1", "2", "3", "4", "5", "q"):
            return choice


def show_history_table(rows: list[dict], total: int, offset: int, limit: int, 
                       search="", platform="All", status="All", sort="Newest") -> None:
    """Shows an upgraded history table with filters and status icons."""
    # Header Panel for Filters
    filter_text = (
        f"🔍 Search: [primary]{search or 'None'}[/]  |  "
        f"Platform: [primary]{platform}[/]  |  "
        f"Status: [primary]{status}[/]  |  "
        f"Sort: [primary]{sort}[/]"
    )
    console.print(Panel(filter_text, title="📊 AURY History Viewer", border_style="primary"))

    table = Table(box=box.ROUNDED, expand=True, border_style="primary")
    table.add_column("#", justify="center", width=4)
    table.add_column("Platform", width=10)
    table.add_column("Title")
    table.add_column("Quality", width=12)
    table.add_column("Size", justify="right", width=10)
    table.add_column("Speed", justify="right", width=10)
    table.add_column("Date", width=12)
    table.add_column("Status", width=10)

    for i, row in enumerate(rows, 1):
        idx = offset + i
        
        # Status styling
        st = (row.get("status") or "pending").lower()
        if st == "completed":
            status_cell = Text("✔ Done", style="success")
        elif st == "failed":
            status_cell = Text("✘ Fail", style="error")
        else:
            status_cell = Text("🕒 " + st.capitalize(), style="warning")

        # Size & Speed
        size_str = format_size(row.get("file_size_bytes") or 0)
        speed_str = format_speed(row.get("avg_speed_bps") or 0)
        
        # Date
        dt_str = row.get("downloaded_at", "")
        if dt_str:
            dt_str = dt_str.split(" ")[0] # YYYY-MM-DD
            
        table.add_row(
            str(idx),
            row.get("platform") or "Unknown",
            (row.get("title") or "Unknown")[:40] + "...",
            row.get("quality_label") or "Best",
            size_str,
            speed_str,
            dt_str,
            status_cell
        )

    console.print(table)
    
    page = (offset // limit) + 1
    total_pages = (total + limit - 1) // limit
    console.print(f"  Page {page} of {total_pages}  ([primary]N[/])ext  ([primary]P[/])rev")
    
    console.print(Panel(
        " [F] Filter    [S] Search    [O] Sort      [E] Export CSV\n"
        " [D] Delete    [R] Retry All [C] Clear All  [B] Back",
        title="Actions", border_style="dim"
    ))


def prompt_history_search() -> str:
    return console.input("▶ Search history (title/URL keyword, or press Enter for all) → ").strip().lower()


def prompt_history_action() -> str:
    return console.input("▶ Enter row # to open file, D# to delete, R# to retry failed, X to exit\n  (e.g. 1, D3, R5, N for Next, P for Prev, X to go back) → ").strip().upper()


def show_file_missing(path: str) -> None:
    show_error_panel(
        "✘ File not found",
        f"File missing at saved path: {path}\nWas it moved or deleted?"
    )

def show_schedule_cancelled() -> bool:
    console.print(Panel("Schedule cancelled.", border_style="warning"))
    while True:
        ans = console.input("Return to menu? (y/n) → ").strip().lower()
        if ans in ("y", "yes"): return True
        if ans in ("n", "no"): return False


# ─── FEATURE 5: Settings & DB Stats ─────────────────────────────────────────

def show_settings_menu(df, dq, mw, turbo, sub_def, sub_lang) -> str:
    # Convert dq to label
    dq_label = "Audio only" if dq == "0" else config.QUALITY_MAP.get(dq, ("1080p", ""))[0]
    sub_def_str = "ON" if sub_def.lower() == "true" else "OFF"
    
    console.print(Panel(
        "⚙  AURY Settings\n\n"
        f"[1]  📁  Download folder   :  {df}    [change]\n"
        f"[2]  🎯  Default quality   :  {dq_label}         [change]\n"
        f"[3]  ⚡  Max workers       :  {mw}             [change]\n"
        f"[4]  🚀  aria2c turbo      :  {turbo.upper()}          [toggle]\n"
        f"[5]  📝  Default subtitles :  {sub_def_str}           [toggle]\n"
        f"[6]  🌐  Default sub lang  :  {sub_lang}            [change]\n"
        f"[7]  🗑   Clear history     :               [run]\n"
        f"[8]  📊  Database stats    :               [view]\n"
        f"[9]  🔙  Back to menu",
        border_style="primary",
    ))
    while True:
        choice = console.input("▶ Enter 1–9 → ").strip()
        if choice in [str(i) for i in range(1, 10)]:
            return choice

def prompt_new_folder(current: str) -> str:
    return console.input(f"▶ Enter new folder path (current: {current}) → ").strip()

def prompt_max_workers(current: str) -> str:
    while True:
        val = console.input(f"▶ Enter number of parallel workers (1–16, current: {current}) → ").strip()
        if val.isdigit() and 1 <= int(val) <= 16:
            return val
        console.print("[error]  Please enter a number between 1 and 16.[/]")

def prompt_sub_lang(current: str) -> str:
    val = console.input(f"▶ Enter new default sub lang (e.g. en, hi) (current: {current}) → ").strip().lower()
    return val

def prompt_clear_history_confirm() -> bool:
    val = console.input("▶ Are you sure? This deletes ALL download history. (y/n) → ").strip().lower()
    return val in ("y", "yes")

def show_advanced_stats(stats: dict) -> None:
    # Build Top Platforms table
    tp_text = Text()
    tp_text.append("Top Platforms       Count  Total Size\n", style="bold")
    for r in stats.get("top_platforms", []):
        size = _fmt_bytes(r['s'])
        tp_text.append(f"{r['platform']:<19} {r['c']:<6} {size}\n")
        
    # Build Top Quality table
    tq_text = Text()
    tq_text.append("Top Quality Used    Count\n", style="bold")
    for r in stats.get("top_quality", []):
        tq_text.append(f"{r['quality_label']:<19} {r['c']}\n")

    ldl = stats.get("largest_dl")
    fdl = stats.get("fastest_dl")
    
    ldl_str = "None"
    if ldl:
        date = str(ldl['downloaded_at']).split(' ')[0]
        ldl_str = f"{_fmt_bytes(ldl['file_size_bytes'])} ({ldl['title'][:20]}..., {date})"
        
    fdl_str = "None"
    if fdl:
        date = str(fdl['downloaded_at']).split(' ')[0]
        fdl_str = f"{_fmt_bytes(fdl['avg_speed_bps'])}/s ({date})"

    content = (
        f"Database file  :  aury.db  ({_fmt_bytes(stats['db_size_bytes'])})\n"
        f"Total records  :  {stats['total_dl']} downloads · {stats['total_sessions']} sessions\n\n"
        f"┌──────────────────────────────────────────┐\n"
        f"│ {tp_text.plain.rstrip().replace(chr(10), chr(10)+'│ ')}\n"
        f"└──────────────────────────────────────────┘\n\n"
        f"┌──────────────────────────────────────────┐\n"
        f"│ {tq_text.plain.rstrip().replace(chr(10), chr(10)+'│ ')}\n"
        f"└──────────────────────────────────────────┘\n\n"
        f"All-time avg speed   :  {_fmt_bytes(stats['avg_speed_bps'])}/s\n"
        f"Largest download     :  {ldl_str}\n"
        f"Fastest download     :  {fdl_str}\n"
    )
    
    console.print(Panel(
        content,
        title="📊  AURY Database Statistics",
        border_style="primary"
    ))
    console.input("▶ Press Enter to go back → ")

