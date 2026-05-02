import customtkinter as ctk
from tkinter import filedialog
from core import database, config

class SettingsPage(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app

        # Title
        ctk.CTkLabel(self, text="⚙ Settings", font=ctk.CTkFont(size=24, weight="bold")).pack(anchor="w", padx=20, pady=(20, 30))

        # Folder Setting
        f1 = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=8)
        f1.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f1, text="Download Folder:", width=120, anchor="w").pack(side="left", padx=15, pady=15)
        self.folder_entry = ctk.CTkEntry(f1, width=400)
        self.folder_entry.pack(side="left", padx=10)
        ctk.CTkButton(f1, text="Browse", width=80, command=self._browse).pack(side="left")

        # Quality Setting
        f2 = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=8)
        f2.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f2, text="Default Quality:", width=120, anchor="w").pack(side="left", padx=15, pady=15)
        
        qualities = [f"{k} - {v[0]}" for k, v in config.QUALITY_MAP.items()]
        qualities.insert(0, "0 - Audio only (MP3 320k)")
        self.quality_var = ctk.StringVar(value="4 - 1080p") # Will load later
        ctk.CTkOptionMenu(f2, values=qualities, variable=self.quality_var).pack(side="left", padx=10)

        # Workers Slider
        f3 = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=8)
        f3.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(f3, text="Max Workers:", width=120, anchor="w").pack(side="left", padx=15, pady=15)
        self.workers_var = ctk.IntVar(value=config.MAX_WORKERS)
        self.workers_lbl = ctk.CTkLabel(f3, text=str(config.MAX_WORKERS), width=30)
        self.workers_lbl.pack(side="left")
        ctk.CTkSlider(f3, from_=1, to=16, number_of_steps=15, variable=self.workers_var, command=lambda v: self.workers_lbl.configure(text=str(int(v)))).pack(side="left", padx=10)

        # Switches
        f4 = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=8)
        f4.pack(fill="x", padx=20, pady=10)
        
        self.turbo_var = ctk.BooleanVar()
        ctk.CTkSwitch(f4, text="aria2c Turbo Mode", variable=self.turbo_var).pack(anchor="w", padx=15, pady=15)
        
        self.sub_var = ctk.BooleanVar()
        ctk.CTkSwitch(f4, text="Download Subtitles Automatically", variable=self.sub_var).pack(anchor="w", padx=15, pady=(0, 15))

        # Save Button
        ctk.CTkButton(self, text="💾 Save Settings", fg_color="#2ea043", hover_color="#3fb950", command=self._save).pack(anchor="w", padx=20, pady=30)

    def on_show(self):
        # Load values from DB
        df = database.db.get_setting("download_dir", str(config.DOWNLOAD_DIR))
        self.folder_entry.delete(0, 'end')
        self.folder_entry.insert(0, df)
        
        dq = database.db.get_setting("default_quality", "4")
        if dq == "0":
            self.quality_var.set("0 - Audio only (MP3 320k)")
        elif dq in config.QUALITY_MAP:
            self.quality_var.set(f"{dq} - {config.QUALITY_MAP[dq][0]}")
            
        mw = int(database.db.get_setting("max_workers", str(config.MAX_WORKERS)))
        self.workers_var.set(mw)
        self.workers_lbl.configure(text=str(mw))
        
        self.turbo_var.set(database.db.get_setting("aria2c_turbo", "auto") != "off")
        self.sub_var.set(database.db.get_setting("default_subtitles", "False") == "True")

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.folder_entry.get())
        if d:
            self.folder_entry.delete(0, 'end')
            self.folder_entry.insert(0, d)

    def _save(self):
        database.db.set_setting("download_dir", self.folder_entry.get())
        
        q_val = self.quality_var.get().split(" - ")[0]
        database.db.set_setting("default_quality", q_val)
        
        database.db.set_setting("max_workers", str(int(self.workers_var.get())))
        database.db.set_setting("aria2c_turbo", "auto" if self.turbo_var.get() else "off")
        database.db.set_setting("default_subtitles", "True" if self.sub_var.get() else "False")
        
        # Reload config in backend
        config.init_config()
