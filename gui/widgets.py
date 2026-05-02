import customtkinter as ctk

class NavButton(ctk.CTkButton):
    def __init__(self, master, text, command, **kwargs):
        super().__init__(
            master, 
            text=text, 
            command=command,
            fg_color="transparent",
            text_color=("black", "white"),
            hover_color=("#e5e7eb", "#1f2937"),
            anchor="w",
            height=40,
            corner_radius=0,
            font=ctk.CTkFont(size=14),
            **kwargs
        )
        self.is_active = False

    def set_active(self, active: bool):
        self.is_active = active
        if active:
            self.configure(
                fg_color="#1f6feb", 
                text_color="white",
                hover_color="#1f6feb"
            )
        else:
            self.configure(
                fg_color="transparent", 
                text_color=("black", "white"),
                hover_color=("#e5e7eb", "#1f2937")
            )

class StatCard(ctk.CTkFrame):
    def __init__(self, master, value, label, **kwargs):
        super().__init__(master, fg_color=("#f6f8fa", "#161b22"), corner_radius=8, **kwargs)
        
        self.value_label = ctk.CTkLabel(
            self, 
            text=value, 
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("black", "white")
        )
        self.value_label.pack(pady=(15, 0))

        self.desc_label = ctk.CTkLabel(
            self, 
            text=label, 
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.desc_label.pack(pady=(0, 15))

    def update_val(self, value):
        self.value_label.configure(text=value)

class ActiveDownloadCard(ctk.CTkFrame):
    def __init__(self, master, title, info, progress, **kwargs):
        super().__init__(master, fg_color=("#f6f8fa", "#21262d"), corner_radius=8, **kwargs)
        
        # Title
        self.title_label = ctk.CTkLabel(self, text=title, font=ctk.CTkFont(weight="bold"), anchor="w")
        self.title_label.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        # Progress bar
        self.progress = ctk.CTkProgressBar(self, height=8, progress_color="#2ea043")
        self.progress.set(progress)
        self.progress.grid(row=0, column=1, sticky="e", padx=10, pady=(10, 0))
        
        self.pct_label = ctk.CTkLabel(self, text=f"{int(progress*100)}%", font=ctk.CTkFont(size=12))
        self.pct_label.grid(row=0, column=2, sticky="e", padx=(0, 10), pady=(10, 0))
        
        # Info row (1080p · YouTube · 18.4 MB/s)
        self.info_label = ctk.CTkLabel(self, text=info, font=ctk.CTkFont(size=11), text_color="gray", anchor="w")
        self.info_label.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=(0, 10))

        self.grid_columnconfigure(0, weight=1)

    def update_progress(self, progress, info):
        self.progress.set(progress)
        self.pct_label.configure(text=f"{int(progress*100)}%")
        self.info_label.configure(text=info)
