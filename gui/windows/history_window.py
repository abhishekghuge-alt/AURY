import os
import subprocess
import customtkinter as ctk
from core import database
from gui import theme

class HistoryWindow(ctk.CTkFrame):
    def __init__(self, master, main_window, **kwargs):
        super().__init__(master, **kwargs)
        self.main_window = main_window
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.title = ctk.CTkLabel(self.header, text="Download History", font=theme.get_fonts()["heading"])
        self.title.pack(side="left", padx=10)
        
        self.btn_refresh = ctk.CTkButton(self.header, text="🔄 Refresh", width=100, command=self.refresh_data)
        self.btn_refresh.pack(side="right", padx=10)

        # Scrollable Area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(1, weight=1)

    def refresh_data(self):
        # Clear existing
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        history = database.get_all_history(limit=100)
        
        # Table Headers
        headers = ["Status", "Title", "Size", "Action"]
        for i, h in enumerate(headers):
            lbl = ctk.CTkLabel(self.scroll_frame, text=h, font=theme.get_fonts()["badge"], text_color="gray50")
            lbl.grid(row=0, column=i, padx=10, pady=5, sticky="w")

        for i, dl in enumerate(history, 1):
            color = theme.get_status_color(dl['status'])
            
            # Status Badge
            badge = ctk.CTkLabel(
                self.scroll_frame, text=dl['status'].upper(), 
                font=theme.get_fonts()["badge"], fg_color=color, text_color="black", 
                width=80, corner_radius=5
            )
            badge.grid(row=i, column=0, padx=10, pady=5)

            # Title
            title = ctk.CTkLabel(self.scroll_frame, text=dl['title'] or "Unknown", font=theme.get_fonts()["body"], anchor="w")
            title.grid(row=i, column=1, padx=10, pady=5, sticky="ew")

            # Size
            size_mb = f"{dl['file_size'] / (1024**2):.1f} MB" if dl['file_size'] else "-"
            size_lbl = ctk.CTkLabel(self.scroll_frame, text=size_mb, font=theme.get_fonts()["small"])
            size_lbl.grid(row=i, column=2, padx=10, pady=5)

            # Actions
            btn_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
            btn_frame.grid(row=i, column=3, padx=10, pady=5)
            
            if dl['status'] == 'completed' and dl['file_path']:
                btn_open = ctk.CTkButton(
                    btn_frame, text="📂", width=30, 
                    command=lambda p=dl['file_path']: self.open_file(p)
                )
                btn_open.pack(side="left", padx=2)
            
            btn_del = ctk.CTkButton(
                btn_frame, text="🗑", width=30, fg_color="transparent", 
                border_width=1, command=lambda sid=dl['session_id']: self.delete_session(sid)
            )
            btn_del.pack(side="left", padx=2)

    def open_file(self, path):
        if os.path.exists(path):
            if os.name == 'nt':
                os.startfile(path)
            else:
                subprocess.call(['xdg-open', path])

    def delete_session(self, session_id):
        database.delete_session(session_id)
        self.refresh_data()
