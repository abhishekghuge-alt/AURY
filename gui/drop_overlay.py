import customtkinter as ctk

class DropOverlay(ctk.CTkFrame):
    def __init__(self, master):
        # We use a very dark color to simulate an overlay. 
        # True transparency (RGBA) isn't natively supported by CTkFrame on all platforms.
        super().__init__(
            master, 
            fg_color=("#374151", "#000000"), # Dark gray in light, pure black in dark
            corner_radius=0
        )
        self.label = ctk.CTkLabel(
            self, 
            text="📥 Drop URL or .txt to Download", 
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="white"
        )
        self.label.pack(expand=True)
        
        # Sub-text
        self.sub_label = ctk.CTkLabel(
            self,
            text="Supports YouTube, Instagram, SoundCloud links",
            font=ctk.CTkFont(size=14),
            text_color="gray"
        )
        self.sub_label.place(relx=0.5, rely=0.6, anchor="center")

    def show(self):
        self.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.lift()

    def hide(self):
        self.place_forget()
