import customtkinter as ctk
from gui import theme

class SettingsWindow(ctk.CTkFrame):
    def __init__(self, master, main_window, **kwargs):
        super().__init__(master, **kwargs)
        self.main_window = main_window
        self.settings = main_window.settings

        self.grid_columnconfigure(0, weight=1)

        # Download Path
        self.path_frame = ctk.CTkFrame(self)
        self.path_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.path_frame, text="Download Directory:", font=theme.get_fonts()["body"]).pack(side="left", padx=10, pady=10)
        self.entry_path = ctk.CTkEntry(self.path_frame, width=400)
        self.entry_path.insert(0, self.settings['download_dir'])
        self.entry_path.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        self.btn_browse = ctk.CTkButton(self.path_frame, text="Browse", width=80, command=self.browse_path)
        self.btn_browse.pack(side="left", padx=10, pady=10)

        # Performance
        self.perf_frame = ctk.CTkFrame(self)
        self.perf_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.perf_frame, text="Max Concurrent Workers:", font=theme.get_fonts()["body"]).pack(side="left", padx=10, pady=10)
        self.slider_workers = ctk.CTkSlider(self.perf_frame, from_=1, to=12, number_of_steps=11)
        self.slider_workers.set(self.settings['max_workers'])
        self.slider_workers.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        # Appearance
        self.look_frame = ctk.CTkFrame(self)
        self.look_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(self.look_frame, text="Theme Mode:", font=theme.get_fonts()["body"]).pack(side="left", padx=10, pady=10)
        self.theme_switch = ctk.CTkSwitch(
            self.look_frame, text="Dark Mode", 
            command=self.toggle_theme,
            onvalue="dark", offvalue="light"
        )
        if self.settings['appearance'] == "dark":
            self.theme_switch.select()
        self.theme_switch.pack(side="left", padx=10)

        # Actions
        self.btn_save = ctk.CTkButton(
            self, text="💾 Save Settings", height=40, fg_color=theme.get_status_color("completed"),
            text_color="black", command=self.save_all
        )
        self.btn_save.pack(pady=30)

    def browse_path(self):
        path = ctk.filedialog.askdirectory()
        if path:
            self.entry_path.delete(0, "end")
            self.entry_path.insert(0, path)

    def toggle_theme(self):
        mode = self.theme_switch.get()
        ctk.set_appearance_mode(mode)

    def save_all(self):
        new_settings = {
            "download_dir": self.entry_path.get(),
            "max_workers": int(self.slider_workers.get()),
            "appearance": self.theme_switch.get(),
            "theme": "blue",
            "auto_open": False,
            "speed_limit": "0"
        }
        theme.save_settings(new_settings)
        self.main_window.settings = new_settings
        self.main_window.show_toast("Success", "Settings saved successfully.")
