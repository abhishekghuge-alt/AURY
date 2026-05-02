import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_TEXT, DND_FILES
from gui.dashboard import DashboardPage
from gui.history import HistoryPage
from gui.settings import SettingsPage
from gui.widgets import NavButton
from gui.drop_overlay import DropOverlay
from gui.db_report import DBReportPage

from core import database

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AuryApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkinterDnD_Init()
        self.title("AURY — Smart Media Downloader")
        self.geometry("1100x700")
        self.minsize(900, 600)
        self.configure(fg_color=("#ffffff", "#0d1117"))  # Light/Dark BG

        # Load saved theme
        saved_theme = database.db.get_setting("theme", "dark")
        ctk.set_appearance_mode(saved_theme.capitalize())

        # Configure grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # LEFT SIDEBAR
        self._build_sidebar()

        # RIGHT CONTENT AREA
        self.pages = {}
        self._build_content_area()

        # Default: show Dashboard
        self.show_page("dashboard")

        # DROP OVERLAY
        self.overlay = DropOverlay(self)
        
        # DnD Registration
        self.drop_target_register(DND_TEXT, DND_FILES)
        self.dnd_bind("<<DragEnter>>", self._on_drag_enter)
        self.dnd_bind("<<DragLeave>>", self._on_drag_leave)
        self.dnd_bind("<<Drop>>",      self._on_drop)

        # Global Shortcuts
        self._bind_shortcuts()

    def set_tray_icon(self, icon):
        self.tray_icon = icon
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        self.withdraw()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.notify("AURY is still running", "Downloads continue in background.")

    def quit_app(self):
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.destroy()
        import sys
        sys.exit(0)

    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda e: self.pages["dashboard"].open_download_modal())
        self.bind("<Control-q>", lambda e: self.pages["dashboard"].open_download_modal(is_quick=True))
        self.bind("<Control-h>", lambda e: self.show_page("history"))
        self.bind("<Control-comma>", lambda e: self.show_page("settings"))
        self.bind("<Control-d>", lambda e: self.show_page("dashboard"))
        
        # Escape handling for modals is generally handled per-modal, but we can do a global close if needed
        # We will add Escape to DownloadModal in dashboard.py
        
        self.bind("<F5>", lambda e: self._refresh_current_page())
        
        # Clipboard check for Ctrl+V
        self.bind("<Control-v>", lambda e: self._handle_paste())

    def _refresh_current_page(self):
        for name, page in self.pages.items():
            if self.btn_dashboard.cget("fg_color") != "transparent" and name == "dashboard": # active
                page.on_show()
            elif hasattr(page, 'on_show') and page.winfo_ismapped():
                page.on_show()

    def _handle_paste(self):
        try:
            clip = self.clipboard_get()
            if clip.startswith("http"):
                self.show_page("dashboard")
                self.pages["dashboard"].open_download_modal(initial_url=clip)
        except:
            pass

    def _build_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=("#f6f8fa", "#161b22"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)  # Spacer

        # Logo
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="🔴 AURY", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Nav Buttons
        self.btn_dashboard = NavButton(self.sidebar, text="⬇ Dashboard      Ctrl+D", command=lambda: self.show_page("dashboard"))
        self.btn_dashboard.grid(row=1, column=0, sticky="ew")

        self.btn_history = NavButton(self.sidebar, text="📋 History        Ctrl+H", command=lambda: self.show_page("history"))
        self.btn_history.grid(row=2, column=0, sticky="ew")

        self.btn_settings = NavButton(self.sidebar, text="⚙ Settings       Ctrl+,", command=lambda: self.show_page("settings"))
        self.btn_settings.grid(row=3, column=0, sticky="ew")

        self.btn_db_report = NavButton(self.sidebar, text="🎓 DB Report", command=lambda: self.show_page("db_report"))
        self.btn_db_report.grid(row=4, column=0, sticky="ew")

        # Footer (Theme Toggle)
        self.theme_btn = ctk.CTkButton(
            self.sidebar, 
            text="", 
            command=self.toggle_theme,
            fg_color="transparent",
            hover_color="#1f2937"
        )
        self.theme_btn.grid(row=5, column=0, padx=20, pady=10, sticky="s")
        
        saved_theme = database.db.get_setting("theme", "dark")
        self._update_theme_btn(saved_theme.capitalize())

        self.footer_label = ctk.CTkLabel(self.sidebar, text="V2.0", text_color="gray")
        self.footer_label.grid(row=6, column=0, padx=20, pady=20, sticky="s")

    def toggle_theme(self):
        current = ctk.get_appearance_mode()
        new = "Light" if current == "Dark" else "Dark"
        ctk.set_appearance_mode(new)
        database.db.set_setting("theme", new.lower())
        self._update_theme_btn(new)

    def _update_theme_btn(self, mode):
        icon = "🌙" if mode == "Light" else "☀"
        label = "Dark" if mode == "Light" else "Light"
        self.theme_btn.configure(text=f"{icon} {label}")

    def _on_drag_enter(self, event):
        self.overlay.show()

    def _on_drag_leave(self, event):
        self.overlay.hide()

    def _on_drop(self, event):
        self.overlay.hide()
        data = event.data.strip()
        
        # Clean data (some browsers add {} or other chars)
        if data.startswith("{") and data.endswith("}"):
            data = data[1:-1]
            
        if data.startswith("http"):
            self.show_page("dashboard")
            self.pages["dashboard"].open_download_modal(initial_url=data)
        elif data.lower().endswith(".txt"):
            try:
                import os
                if os.path.exists(data):
                    with open(data, 'r', encoding='utf-8') as f:
                        urls = [l.strip() for l in f if l.strip().startswith("http")]
                        if urls:
                            self.show_page("dashboard")
                            self.pages["dashboard"].open_batch_modal(urls)
            except Exception as e:
                print(f"Error reading dropped file: {e}")

    def _build_content_area(self):
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Initialize pages
        self.pages["dashboard"] = DashboardPage(self.content_frame, self)
        self.pages["history"] = HistoryPage(self.content_frame, self)
        self.pages["settings"] = SettingsPage(self.content_frame, self)
        self.pages["db_report"] = DBReportPage(self.content_frame, self)

        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def show_page(self, name: str):
        # Reset nav buttons
        self.btn_dashboard.set_active(name == "dashboard")
        self.btn_history.set_active(name == "history")
        self.btn_settings.set_active(name == "settings")
        self.btn_db_report.set_active(name == "db_report")

        # Bring page to front
        page = self.pages.get(name)
        if page:
            page.tkraise()
            if hasattr(page, 'on_show'):
                page.on_show()
