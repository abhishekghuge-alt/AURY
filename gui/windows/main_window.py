import customtkinter as ctk
from core import config, downloader
from gui import theme
from gui.windows.download_panel import DownloadPanel
from gui.windows.history_window import HistoryWindow
from gui.windows.settings_window import SettingsWindow

class MainWindow(ctk.CTk):
    def __init__(self, settings):
        super().__init__()
        
        self.settings = settings
        self.title(f"{config.APP_NAME} — Smart Media Downloader")
        self.geometry("1100x700")
        self.minsize(1000, 650)
        
        # Grid layout (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)
        
        self.logo_label = ctk.CTkLabel(
            self.sidebar, text="AURY", 
            font=theme.get_fonts()["heading"], text_color=config.HEX_PRIMARY
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.btn_download = ctk.CTkButton(
            self.sidebar, text="⬇ Download", command=self.show_download,
            fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
            anchor="w"
        )
        self.btn_download.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_history = ctk.CTkButton(
            self.sidebar, text="📋 History", command=self.show_history,
            fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
            anchor="w"
        )
        self.btn_history.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.btn_settings = ctk.CTkButton(
            self.sidebar, text="⚙ Settings", command=self.show_settings,
            fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
            anchor="w"
        )
        self.btn_settings.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.version_label = ctk.CTkLabel(self.sidebar, text=f"v{config.APP_VERSION}", font=theme.get_fonts()["small"], text_color="gray50")
        self.version_label.grid(row=5, column=0, padx=20, pady=10)

        # Content Area
        self.content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(0, weight=1)

        # Initialize Panels
        self.download_panel = DownloadPanel(self.content_frame, self)
        self.history_window = HistoryWindow(self.content_frame, self)
        self.settings_window = SettingsWindow(self.content_frame, self)

        self.show_download()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def show_download(self):
        self._clear_content()
        self.download_panel.grid(row=0, column=0, sticky="nsew")
        self.btn_download.configure(fg_color=("gray75", "gray25"))

    def show_history(self):
        self._clear_content()
        self.history_window.grid(row=0, column=0, sticky="nsew")
        self.history_window.refresh_data()
        self.btn_history.configure(fg_color=("gray75", "gray25"))

    def show_settings(self):
        self._clear_content()
        self.settings_window.grid(row=0, column=0, sticky="nsew")
        self.btn_settings.configure(fg_color=("gray75", "gray25"))

    def _clear_content(self):
        self.download_panel.grid_forget()
        self.history_window.grid_forget()
        self.settings_window.grid_forget()
        for btn in [self.btn_download, self.btn_history, self.btn_settings]:
            btn.configure(fg_color="transparent")

    def show_toast(self, title, message):
        """Feature 5: Post-download notification toast."""
        toast = ctk.CTkFrame(self, fg_color=theme.get_status_color("completed"), corner_radius=10)
        toast.place(relx=0.95, rely=0.95, anchor="se")
        lbl = ctk.CTkLabel(toast, text=f"✔ {title}\n{message}", font=theme.get_fonts()["small"], text_color="black")
        lbl.pack(padx=20, pady=10)
        self.after(4000, toast.destroy)

    def on_closing(self):
        downloader.stop_event.set()
        self.destroy()
