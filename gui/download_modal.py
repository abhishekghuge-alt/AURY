import customtkinter as ctk
import threading
import urllib.request
import io
import os
from PIL import Image
import yt_dlp
from core import config, database

class DownloadModal(ctk.CTkToplevel):
    def __init__(self, master, url, on_start):
        super().__init__(master)
        self.title("⬇ New Download")
        self.geometry("600x550")
        self.resizable(False, False)
        
        # Make modal
        self.transient(master)
        self.grab_set()

        self.url = url
        self.on_start = on_start
        self.video_info = None

        # Layout
        self.grid_columnconfigure(1, weight=1)

        # Escape and Ctrl+W to close
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Control-w>", lambda e: self.destroy())

        # URL Input
        ctk.CTkLabel(self, text="URL:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        if url:
            self.url_var = ctk.StringVar(value=url)
            self.url_entry = ctk.CTkEntry(self, textvariable=self.url_var, state="disabled", text_color="gray")
        else:
            self.url_var = ctk.StringVar()
            self.url_entry = ctk.CTkEntry(self, textvariable=self.url_var, placeholder_text="Paste link here...")
            try:
                clip = self.clipboard_get()
                if clip.startswith("http"):
                    self.url_entry.insert(0, clip)
            except:
                pass
            self.url_entry.focus()
            
        self.url_entry.grid(row=0, column=1, padx=(20, 10), pady=(20, 10), sticky="ew")
        
        self.btn_preview = ctk.CTkButton(self, text="🔍 Preview", width=80, command=self._start_preview)
        self.btn_preview.grid(row=0, column=2, padx=(0, 20), pady=(20, 10))

        # Preview Area
        self.preview_frame = ctk.CTkFrame(self, height=120, fg_color=("#e5e7eb", "#161b22"))
        self.preview_frame.grid(row=1, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        self.preview_frame.grid_propagate(False)
        
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="Click 'Preview' to see video info", text_color="gray")
        self.preview_label.pack(expand=True)

        # Settings
        settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        settings_frame.grid(row=2, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
        settings_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(settings_frame, text="Quality:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=(0, 20), pady=10, sticky="w")
        
        qualities = [f"{k} - {v[0]}" for k, v in config.QUALITY_MAP.items()]
        qualities.insert(0, "0 - Audio only (MP3 320k)")
        self.quality_var = ctk.StringVar(value="4 - 1080p")
        self.quality_menu = ctk.CTkOptionMenu(settings_frame, values=qualities, variable=self.quality_var, command=self._update_est_size)
        self.quality_menu.grid(row=0, column=1, pady=10, sticky="ew")

        self.size_label = ctk.CTkLabel(settings_frame, text="Est. size: --", text_color="gray")
        self.size_label.grid(row=0, column=2, padx=(10, 0), pady=10, sticky="w")

        # Options
        self.sub_var = ctk.BooleanVar(value=False)
        self.sub_switch = ctk.CTkSwitch(settings_frame, text="Download Subtitles", variable=self.sub_var)
        self.sub_switch.grid(row=1, column=1, pady=10, sticky="w")

        # Action Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=4, column=0, columnspan=3, pady=(20, 0), sticky="ew")
        self.btn_frame.grid_columnconfigure((0, 1), weight=1)

        self.btn_quick = ctk.CTkButton(self.btn_frame, text="⚡ Quick Download", fg_color="#6e7681", hover_color="#8b949e", command=self._quick)
        self.btn_quick.grid(row=0, column=0, padx=20)

        self.btn_start = ctk.CTkButton(self.btn_frame, text="⬇ Start Download", fg_color="#2ea043", hover_color="#3fb950", command=self._start)
        self.btn_start.grid(row=0, column=1, padx=20)

        if url:
            self._start_preview()

    def _start_preview(self):
        url = self.url_var.get().strip()
        if not url: return
        
        # Reset preview UI
        for child in self.preview_frame.winfo_children():
            child.destroy()
        
        self.preview_label = ctk.CTkLabel(self.preview_frame, text="⌛ Fetching info...")
        self.preview_label.pack(expand=True)
        self.btn_preview.configure(state="disabled")
        
        threading.Thread(target=self._fetch_info_thread, args=(url,), daemon=True).start()

    def _fetch_info_thread(self, url):
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'format': 'best'
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self.video_info = info
                self.after(0, lambda: self._update_preview_ui(info))
        except Exception as e:
            self.after(0, lambda: self._show_preview_error(str(e)))

    def _update_preview_ui(self, info):
        self.btn_preview.configure(state="normal")
        for child in self.preview_frame.winfo_children():
            child.destroy()
            
        # Layout inside preview frame
        self.preview_frame.grid_columnconfigure(1, weight=1)
        
        # Thumbnail
        thumb_url = info.get('thumbnail')
        if thumb_url:
            threading.Thread(target=self._load_thumbnail, args=(thumb_url,), daemon=True).start()
        
        self.thumb_label = ctk.CTkLabel(self.preview_frame, text="🖼️", width=160, height=90, fg_color="black", corner_radius=4)
        self.thumb_label.grid(row=0, column=0, rowspan=3, padx=10, pady=10)
        
        # Title
        title = info.get('title', 'Unknown Title')
        title_label = ctk.CTkLabel(self.preview_frame, text=title[:60] + "..." if len(title)>60 else title, 
                                   font=ctk.CTkFont(size=14, weight="bold"), anchor="w", justify="left")
        title_label.grid(row=0, column=1, sticky="nw", padx=(0, 10), pady=(10, 0))
        
        # Meta info
        duration = info.get('duration')
        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
        uploader = info.get('uploader', 'Unknown')
        extractor = info.get('extractor_key', 'Unknown')
        
        meta_str = f"⏱ {duration_str}  ·  📺 {extractor}\n👤 {uploader}"
        meta_label = ctk.CTkLabel(self.preview_frame, text=meta_str, font=ctk.CTkFont(size=12), text_color="gray", anchor="w", justify="left")
        meta_label.grid(row=1, column=1, sticky="nw", padx=(0, 10))
        
        self._update_est_size()

    def _load_thumbnail(self, url):
        try:
            # Download to memory
            with urllib.request.urlopen(url) as response:
                data = response.read()
            
            img = Image.open(io.BytesIO(data))
            img = img.resize((160, 90), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(160, 90))
            
            self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
        except:
            pass

    def _show_preview_error(self, error):
        self.btn_preview.configure(state="normal")
        for child in self.preview_frame.winfo_children():
            child.destroy()
        msg = "⚠ Preview unavailable — download will still work"
        self.preview_label = ctk.CTkLabel(self.preview_frame, text=msg, text_color="#d29922")
        self.preview_label.pack(expand=True)

    def _update_est_size(self, *args):
        if not self.video_info: return
        
        q_label, q_fmt = self._get_selected_quality()
        
        # Try to find format size
        formats = self.video_info.get('formats', [])
        best_size = None
        
        # Rough estimation logic based on quality label
        target_res = q_label.split(" - ")[-1].lower() if " - " in q_label else ""
        
        for f in formats:
            if target_res in f.get('format_note', '').lower() or target_res in f.get('height', ''):
                if f.get('filesize'):
                    best_size = f['filesize']
                    break
        
        if not best_size and self.video_info.get('filesize_approx'):
            best_size = self.video_info.get('filesize_approx')
            
        if best_size:
            size_mb = best_size / (1024*1024)
            self.size_label.configure(text=f"Est. size: ~{size_mb:.1f} MB")
        else:
            self.size_label.configure(text="Est. size: unknown")

    def _get_selected_quality(self):
        val = self.quality_var.get()
        idx = val.split(" - ")[0]
        if idx == "0":
            return "Audio only (MP3 320k)", "bestaudio/best"
        return config.QUALITY_MAP.get(idx, ("1080p", "bestvideo[height<=1080]+bestaudio/best"))

    def _start(self):
        u = self.url_var.get().strip()
        if not u: return
        q_label, q_fmt = self._get_selected_quality()
        subs = ["en"] if self.sub_var.get() else None
        self.on_start(u, q_label, q_fmt, subs, False)
        self.destroy()

    def _quick(self):
        u = self.url_var.get().strip()
        if not u: return
        default_q = database.db.get_setting("default_quality", "4")
        if default_q not in config.QUALITY_MAP: default_q = "4"
        q_label, q_fmt = config.QUALITY_MAP[default_q]
        
        self.on_start(u, q_label, q_fmt, None, True)
        self.destroy()

class BatchDownloadModal(ctk.CTkToplevel):
    def __init__(self, master, urls, on_start):
        super().__init__(master)
        self.title("📋 Batch Download")
        self.geometry("500x400")
        
        self.transient(master)
        self.grab_set()
        
        self.urls = urls
        self.on_start = on_start
        
        ctk.CTkLabel(self, text=f"Detected {len(urls)} URLs:", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        self.textbox = ctk.CTkTextbox(self, height=200)
        self.textbox.pack(padx=20, pady=10, fill="both", expand=True)
        for url in urls:
            self.textbox.insert("end", url + "\n")
            
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=20)
        
        self.btn_cancel = ctk.CTkButton(self.btn_frame, text="Cancel", fg_color="#6e7681", command=self.destroy)
        self.btn_cancel.pack(side="left", padx=10)
        
        self.btn_queue = ctk.CTkButton(self.btn_frame, text=f"Queue {len(urls)} All", fg_color="#2ea043", command=self._queue_all)
        self.btn_queue.pack(side="left", padx=10)

    def _queue_all(self):
        # Use default quality for batch
        default_q = database.db.get_setting("default_quality", "4")
        if default_q not in config.QUALITY_MAP: default_q = "4"
        q_label, q_fmt = config.QUALITY_MAP[default_q]
        
        for url in self.urls:
            self.on_start(url, q_label, q_fmt, None, True)
        self.destroy()
