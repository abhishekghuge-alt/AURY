import queue
import threading
import pyperclip
import customtkinter as ctk
from concurrent.futures import ThreadPoolExecutor
from core import config, database, downloader
from gui import theme

class DownloadCard(ctk.CTkFrame):
    def __init__(self, master, dl_id, title, **kwargs):
        super().__init__(master, **kwargs)
        self.dl_id = dl_id
        
        self.grid_columnconfigure(1, weight=1)
        
        self.title_label = ctk.CTkLabel(self, text=title[:55], font=theme.get_fonts()["body"], anchor="w")
        self.title_label.grid(row=0, column=0, columnspan=2, padx=10, pady=(5, 0), sticky="ew")
        
        self.progress_bar = ctk.CTkProgressBar(self, height=10)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        
        self.stats_label = ctk.CTkLabel(self, text="Waiting...", font=theme.get_fonts()["small"], text_color="gray60")
        self.stats_label.grid(row=2, column=0, padx=10, pady=(0, 5), sticky="w")
        
        self.status_badge = ctk.CTkLabel(
            self, text="QUEUED", font=theme.get_fonts()["badge"],
            fg_color=theme.get_status_color("queued"), text_color="black", corner_radius=5
        )
        self.status_badge.grid(row=2, column=1, padx=10, pady=(0, 5), sticky="e")

    def update_progress(self, data):
        if data['status'] == 'downloading':
            p = data['downloaded_bytes'] / data['total_bytes'] if data['total_bytes'] else 0
            self.progress_bar.set(p)
            mb_s = data['speed'] / (1024**2)
            self.stats_label.configure(text=f"{mb_s:.1f} MB/s | {p*100:.1f}% | ETA: {data['eta']}s")
            self.status_badge.configure(text="DOWNLOADING", fg_color=theme.get_status_color("downloading"))
        elif data['status'] == 'finished':
            self.progress_bar.set(1.0)
            self.stats_label.configure(text="Download Complete")
            self.status_badge.configure(text="DONE", fg_color=theme.get_status_color("completed"))

class DownloadPanel(ctk.CTkFrame):
    def __init__(self, master, main_window, **kwargs):
        super().__init__(master, **kwargs)
        self.main_window = main_window
        self.update_queue = queue.Queue()
        self.cards = {} # dl_id -> card

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Row 1: URL Input
        self.url_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.url_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_text = ctk.CTkTextbox(self.url_frame, height=100, font=theme.get_fonts()["mono"])
        self.url_text.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.url_text.insert("1.0", "Paste URLs here (one per line)...")

        self.url_btns = ctk.CTkFrame(self.url_frame, fg_color="transparent")
        self.url_btns.grid(row=0, column=1, sticky="ns")
        
        self.btn_paste = ctk.CTkButton(self.url_btns, text="📋 Paste", width=80, command=self.paste_clipboard)
        self.btn_paste.pack(pady=5)
        self.btn_clear = ctk.CTkButton(self.url_btns, text="✕ Clear", width=80, command=lambda: self.url_text.delete("1.0", "end"))
        self.btn_clear.pack(pady=5)

        # Row 2: Options
        self.opt_frame = ctk.CTkFrame(self)
        self.opt_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20), padx=2)
        
        self.quality_var = ctk.StringVar(value="1080p (Recommended)")
        self.quality_menu = ctk.CTkOptionMenu(
            self.opt_frame, values=[v[0] for v in config.QUALITY_MAP.values()],
            variable=self.quality_var
        )
        self.quality_menu.pack(side="left", padx=10, pady=10)

        self.audio_only_var = ctk.BooleanVar(value=False)
        self.audio_check = ctk.CTkCheckBox(self.opt_frame, text="Audio Only (MP3)", variable=self.audio_only_var)
        self.audio_check.pack(side="left", padx=10)

        # Row 3: Action Bar
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        self.btn_start = ctk.CTkButton(
            self.action_frame, text="▶ Start Downloads", fg_color=config.HEX_SUCCESS, 
            text_color="black", hover_color="#00dd00", command=self.start_downloads
        )
        self.btn_start.pack(side="left", padx=(0, 10))

        self.btn_pause = ctk.CTkButton(self.action_frame, text="⏸ Pause All", width=100, command=lambda: downloader.pause_event.clear())
        self.btn_pause.pack(side="left", padx=5)
        
        self.btn_resume = ctk.CTkButton(self.action_frame, text="▶ Resume All", width=100, command=lambda: downloader.pause_event.set())
        self.btn_resume.pack(side="left", padx=5)

        self.btn_stop = ctk.CTkButton(self.action_frame, text="⏹ Stop All", width=100, fg_color=config.HEX_ERROR, command=self.stop_all)
        self.btn_stop.pack(side="left", padx=5)

        # Row 4: Queue Area
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Download Queue")
        self.scroll_frame.grid(row=3, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self._poll_queue()

    def paste_clipboard(self):
        try:
            self.url_text.insert("end", f"\n{pyperclip.paste()}")
        except:
            pass

    def start_downloads(self):
        content = self.url_text.get("1.0", "end").strip()
        urls = [line.strip() for line in content.split("\n") if line.strip().startswith("http")]
        
        if not urls:
            return

        q_label = self.quality_var.get()
        if self.audio_only_var.get():
            q_label, q_fmt = config.QUALITY_MAP["0"]
        else:
            q_fmt = next(v[1] for v in config.QUALITY_MAP.values() if v[0] == q_label)

        downloader.stop_event.clear()
        downloader.pause_event.set()

        # Run in thread pool
        threading.Thread(target=self._run_executor, args=(urls, q_label, q_fmt), daemon=True).start()

    def _run_executor(self, urls, q_label, q_fmt):
        with ThreadPoolExecutor(max_workers=self.main_window.settings['max_workers']) as executor:
            session_id = database.start_session()
            for url in urls:
                worker = downloader.DownloadWorker(
                    session_id, url, q_label, q_fmt, 
                    progress_callback=lambda d: self.update_queue.put(d)
                )
                executor.submit(worker.run)

    def _poll_queue(self):
        """Thread-safe UI updates from the background workers."""
        try:
            while True:
                data = self.update_queue.get_nowait()
                dl_id = data['dl_id']
                if dl_id not in self.cards:
                    card = DownloadCard(self.scroll_frame, dl_id, data['filename'])
                    card.pack(fill="x", padx=5, pady=5)
                    self.cards[dl_id] = card
                
                self.cards[dl_id].update_progress(data)
                
                if data['status'] == 'finished':
                    self.main_window.show_toast("Download Finished", data['filename'])
        except queue.Empty:
            pass
        self.after(200, self._poll_queue)

    def stop_all(self):
        downloader.stop_event.set()
