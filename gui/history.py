import customtkinter as ctk
import platform
import os
import subprocess

from core import database

class HistoryPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        # Search Bar Row
        self.top_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=20, pady=20)
        
        self.search_entry = ctk.CTkEntry(self.top_frame, placeholder_text="🔍 Search title, URL...", width=300)
        self.search_entry.pack(side="left", padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: self.refresh_history())
        
        btn_search = ctk.CTkButton(self.top_frame, text="Search", width=80, command=self.refresh_history)
        btn_search.pack(side="left")

        # Table Container
        self.table_frame = ctk.CTkScrollableFrame(self, fg_color="#161b22", corner_radius=8)
        self.table_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Table Header
        self._build_header()

    def _build_header(self):
        hdr = ctk.CTkFrame(self.table_frame, fg_color="#21262d", corner_radius=0)
        hdr.pack(fill="x")
        
        ctk.CTkLabel(hdr, text="#", width=40).pack(side="left")
        ctk.CTkLabel(hdr, text="Title", width=300, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(hdr, text="Platform", width=100, anchor="w").pack(side="left")
        ctk.CTkLabel(hdr, text="Quality", width=80).pack(side="left")
        ctk.CTkLabel(hdr, text="Size", width=80).pack(side="left")
        ctk.CTkLabel(hdr, text="Date", width=120).pack(side="left")
        ctk.CTkLabel(hdr, text="Acts", width=80).pack(side="right", padx=10)

    def on_show(self):
        self.refresh_history()

    def _fmt_bytes(self, b):
        if not b: return "0 MB"
        return f"{b / (1024*1024):.1f} MB" if b < 1024**3 else f"{b / (1024**3):.1f} GB"

    def refresh_history(self):
        for widget in self.table_frame.winfo_children():
            if widget.cget("fg_color") != "#21262d": # Not the header
                widget.destroy()

        search = self.search_entry.get().lower()
        rows = database.db.get_history(limit=100)
        
        filtered = [r for r in rows if search in (r['title'] or '').lower() or search in (r['url'] or '').lower()]

        for i, r in enumerate(filtered, 1):
            row_frame = ctk.CTkFrame(self.table_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)
            
            ctk.CTkLabel(row_frame, text=str(i), width=40).pack(side="left")
            ctk.CTkLabel(row_frame, text=(r['title'] or 'Unknown')[:40], width=300, anchor="w").pack(side="left", padx=10)
            
            plat = f"{r['platform_icon']} {r['platform']}" if r['platform'] else "—"
            ctk.CTkLabel(row_frame, text=plat, width=100, anchor="w").pack(side="left")
            
            ctk.CTkLabel(row_frame, text=r['quality_label'] or '—', width=80).pack(side="left")
            ctk.CTkLabel(row_frame, text=self._fmt_bytes(r['file_size_bytes']), width=80).pack(side="left")
            
            date_str = r['downloaded_at'].split("T")[0]
            ctk.CTkLabel(row_frame, text=date_str, width=120).pack(side="left")
            
            # Actions
            acts = ctk.CTkFrame(row_frame, fg_color="transparent")
            acts.pack(side="right", padx=10)
            
            btn_open = ctk.CTkButton(acts, text="📂", width=30, fg_color="transparent", command=lambda p=r['file_path']: self._open_file(p))
            btn_open.pack(side="left", padx=2)
            
            btn_del = ctk.CTkButton(acts, text="🗑", width=30, fg_color="transparent", hover_color="#f85149", command=lambda id=r['id']: self._delete_record(id))
            btn_del.pack(side="left", padx=2)

    def _open_file(self, path):
        if not path or not os.path.exists(path):
            return
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", path])
        else:
            subprocess.run(["xdg-open", path])

    def _delete_record(self, dl_id):
        database.db.delete_download(dl_id)
        self.refresh_history()
