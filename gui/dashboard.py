import customtkinter as ctk
import queue
import threading
import time

from core import database, config, downloader
from gui.widgets import StatCard
from gui.queue_panel import QueuePanel
from gui.analytics import AnalyticsTab

from gui.download_modal import DownloadModal, BatchDownloadModal

class DashboardPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.progress_queue = queue.Queue()
        self.active_cards = {}  # dl_id -> ActiveDownloadCard
        self.session_id = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self, corner_radius=8)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.tab_dls = self.tabview.add("⬇ Downloads")
        self.tab_analytics = self.tabview.add("📊 Analytics")

        # Setup Tab 1 (Downloads)
        self.tab_dls.grid_columnconfigure(0, weight=6)
        self.tab_dls.grid_columnconfigure(1, weight=4)
        self.tab_dls.grid_rowconfigure(2, weight=1)

        self._build_stats_row(self.tab_dls)
        self._build_middle_row(self.tab_dls)
        self._build_bottom_row(self.tab_dls)

        # Setup Tab 2 (Analytics)
        self.tab_analytics.grid_columnconfigure(0, weight=1)
        self.tab_analytics.grid_rowconfigure(0, weight=1)
        self.analytics_page = AnalyticsTab(self.tab_analytics, app)
        self.analytics_page.grid(row=0, column=0, sticky="nsew")

        self.tabview.configure(command=self._on_tab_change)

        self._update_loop()
        
        # Dashboard specific shortcuts
        self.bind("<space>", self._handle_space)
        self.bind("<Delete>", self._handle_delete)

    def _on_tab_change(self):
        if self.tabview.get() == "📊 Analytics":
            self.analytics_page.on_show()

    def on_show(self):
        self.refresh_stats()
        self.focus_set() # Need focus to receive key events
        if self.tabview.get() == "📊 Analytics":
            self.analytics_page.on_show()

    def _handle_space(self, event):
        # Pause/resume topmost active download
        items = database.db.get_active_queue()
        for it in items:
            if it['status'] in ('downloading', 'pending', 'retrying'):
                self.queue_panel.handle_action(it['id'], 'pause')
                break
            elif it['status'] == 'paused':
                self.queue_panel.handle_action(it['id'], 'resume')
                break

    def _handle_delete(self, event):
        # Remove topmost pending item (since we don't have selection)
        items = database.db.get_active_queue()
        for it in items:
            if it['status'] == 'pending':
                self.queue_panel.handle_action(it['id'], 'remove')
                break

    def _fmt_bytes(self, b):
        if not b: return "0 MB"
        return f"{b / (1024*1024):.1f} MB" if b < 1024**3 else f"{b / (1024**3):.1f} GB"

    def refresh_stats(self):
        stats = database.db.get_stats()
        
        # Basic stats
        self.stat_dls.update_val(f"📦 {stats['total_downloads']}")
        self.stat_saved.update_val(f"💾 {self._fmt_bytes(stats['total_bytes'])}")
        
        # Advanced stats for speed
        adv = database.db.get_advanced_stats()
        speed_mb = adv['avg_speed_bps'] / (1024*1024)
        self.stat_speed.update_val(f"⚡ {speed_mb:.1f} MB/s")

        # Rebuild Platform Breakdown
        for widget in self.platform_frame.winfo_children():
            if widget != self.platform_lbl:
                widget.destroy()

        platforms = database.db.conn.execute("SELECT * FROM v_platform_stats ORDER BY total_downloads DESC LIMIT 5").fetchall()
        total_dls = sum(p['total_downloads'] for p in platforms) or 1
        
        for i, p in enumerate(platforms):
            name = f"{p['icon']} {p['name']}"
            count = p['total_downloads']
            pct = count / total_dls
            
            row = ctk.CTkFrame(self.platform_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            row.grid_columnconfigure(1, weight=1)
            
            ctk.CTkLabel(row, text=name, width=100, anchor="w").grid(row=0, column=0)
            bar = ctk.CTkProgressBar(row, height=10, progress_color="#1f6feb")
            bar.set(pct)
            bar.grid(row=0, column=1, sticky="ew", padx=10)
            ctk.CTkLabel(row, text=f"{int(pct*100)}% ({count})", width=60, anchor="e").grid(row=0, column=2)

        self.refresh_recent()

    def refresh_recent(self):
        for widget in self.recent_inner.winfo_children():
            widget.destroy()

        recent = database.db.get_history(limit=5)
        if not recent:
            ctk.CTkLabel(self.recent_inner, text="No recent downloads.", text_color="gray").pack(pady=20)
            return

        for r in recent:
            status = r['status']
            icon = "✔" if status == 'completed' else "✘" if status == 'failed' else "⏹"
            color = "#3fb950" if status == 'completed' else "#f85149" if status == 'failed' else "gray"
            
            row = ctk.CTkFrame(self.recent_inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row, text=icon, text_color=color, width=30).pack(side="left")
            ctk.CTkLabel(row, text=(r['title'] or 'Unknown')[:40], width=300, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row, text=r['quality_label'] or '—', width=80).pack(side="left")
            ctk.CTkLabel(row, text=self._fmt_bytes(r['file_size_bytes']), width=80).pack(side="left")
            
            date_str = r['downloaded_at'].split("T")[1][:5] if "T" in r['downloaded_at'] else r['downloaded_at'][:16]
            ctk.CTkLabel(row, text=date_str, text_color="gray", width=80).pack(side="right")

    def _build_stats_row(self, parent):
        self.stats_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.stats_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=20)
        
        self.stats_frame.grid_columnconfigure((0,1,2,3), weight=1)

        self.stat_dls = StatCard(self.stats_frame, "📦 0", "Total Downloads")
        self.stat_dls.grid(row=0, column=0, padx=5, sticky="ew")

        self.stat_saved = StatCard(self.stats_frame, "💾 0 MB", "Space Saved")
        self.stat_saved.grid(row=0, column=1, padx=5, sticky="ew")

        self.stat_speed = StatCard(self.stats_frame, "⚡ 0 MB/s", "Avg Speed")
        self.stat_speed.grid(row=0, column=2, padx=5, sticky="ew")

        self.stat_success = StatCard(self.stats_frame, "🎯 100%", "Success Rate")
        self.stat_success.grid(row=0, column=3, padx=5, sticky="ew")

    def _build_middle_row(self, parent):
        # LEFT: Smart Queue Manager
        self.queue_panel = QueuePanel(parent, self.open_download_modal)
        self.queue_panel.grid(row=1, column=0, sticky="nsew", padx=(20, 10), pady=(0, 20))

        # RIGHT: Platform Breakdown
        self.platform_frame = ctk.CTkFrame(parent, fg_color=("#f6f8fa", "#161b22"), corner_radius=8)
        self.platform_frame.grid(row=1, column=1, sticky="nsew", padx=(10, 20), pady=(0, 20))
        
        self.platform_lbl = ctk.CTkLabel(self.platform_frame, text="📊 Platform Breakdown", font=ctk.CTkFont(size=16, weight="bold"))
        self.platform_lbl.pack(anchor="w", padx=15, pady=15)

    def _build_bottom_row(self, parent):
        self.recent_frame = ctk.CTkFrame(parent, fg_color=("#f6f8fa", "#161b22"), corner_radius=8)
        self.recent_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=(0, 20))
        
        lbl = ctk.CTkLabel(self.recent_frame, text="🕐 Recent Downloads", font=ctk.CTkFont(size=16, weight="bold"))
        lbl.pack(anchor="w", padx=15, pady=15)

        self.recent_inner = ctk.CTkFrame(self.recent_frame, fg_color="transparent")
        self.recent_inner.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def open_download_modal(self, initial_url="", is_quick=False):
        url = initial_url or ""
        modal = DownloadModal(self.winfo_toplevel(), url, self.start_download)
        if is_quick and url:
            # If quick and we already have a URL, just run it
            modal._quick()

    def open_batch_modal(self, urls):
        BatchDownloadModal(self.winfo_toplevel(), urls, self.start_download)

    def start_download(self, url, q_label, q_fmt, sub_langs, is_quick):
        if not self.session_id:
            self.session_id = database.db.start_session()

        def progress_cb(data):
            self.progress_queue.put(data)

        w = downloader.DownloadWorker(
            self.session_id, url, q_label, q_fmt,
            progress_callback=progress_cb,
            sub_langs=sub_langs,
            is_quick_mode=is_quick,
        )

        # Register a sentinel so _handle_progress tracks this worker
        temp_id = id(w)
        self.active_cards[temp_id] = True

        self.queue_panel.refresh()

        def run_thread():
            res = w.run()
            self.progress_queue.put({
                "dl_id":    w.dl_id,
                "status":   res.status,
                "temp_id":  temp_id,
                "filename": res.title,
            })
            self.after(0, self.queue_panel.refresh)

        threading.Thread(target=run_thread, daemon=True).start()

    def _update_loop(self):
        for _ in range(50):
            try:
                data = self.progress_queue.get_nowait()
                self._handle_progress(data)
            except queue.Empty:
                break

        self.after(150, self._update_loop)

    def _handle_progress(self, data):
        dl_id   = data.get("dl_id")
        temp_id = data.get("temp_id")
        status  = data.get("status")

        # Promote temp_id sentinel → real dl_id
        if temp_id and temp_id in self.active_cards and dl_id:
            self.active_cards[dl_id] = self.active_cards.pop(temp_id)

        # Auto-register the dl_id on first progress callback (no temp_id yet)
        if dl_id and dl_id not in self.active_cards:
            self.active_cards[dl_id] = True

        if not dl_id:
            return

        if status == "downloading":
            dl    = float(data.get("downloaded_bytes") or 0)
            total = float(data.get("total_bytes") or 1)
            pct   = min(dl / total, 1.0) if total > 0 else 0

            speed_mb = float(data.get("speed") or 0) / (1024 * 1024)
            eta      = int(data.get("eta") or 0)
            info     = f"{speed_mb:.1f} MB/s · ETA: {eta}s"
            self.queue_panel.update_card(dl_id, pct, info)

        elif status == "retrying":
            att  = data.get("attempt", 1)
            mx   = data.get("max_retries", 3)
            wait = data.get("wait", 0)
            self.queue_panel.update_card(dl_id, 0.5, f"⚠️ Retrying {att}/{mx} in {wait}s...")

        elif status in ("finished", "failed", "stopped"):
            if dl_id in self.active_cards:
                del self.active_cards[dl_id]

            if status == "finished":
                self.queue_panel.update_card(dl_id, 1.0, "✔ Completed")
            else:
                self.queue_panel.update_card(dl_id, 0.0, f"✘ {status.capitalize()}")

            self.refresh_stats()
            self.after(2000, self.queue_panel.refresh)
