import customtkinter as ctk
import os
import threading
from core import database, config, downloader

class QueueCard(ctk.CTkFrame):
    def __init__(self, master, data, on_action):
        super().__init__(master, fg_color=("#f6f8fa", "#161b22"), corner_radius=8)
        self.data = data
        self.dl_id = data['id']
        self.on_action = on_action

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure((0, 1), weight=1)

        # Title
        title = data.get('title') or data.get('url')
        self.title_label = ctk.CTkLabel(self, text=title[:60] + ("..." if len(title)>60 else ""), 
                                        font=ctk.CTkFont(weight="bold"))
        self.title_label.grid(row=0, column=1, sticky="w", padx=15, pady=(10, 0))

        # Subtitle info
        info = f"{data.get('quality_label')} · {data.get('platform')}"
        self.info_label = ctk.CTkLabel(self, text=info, text_color="gray", font=ctk.CTkFont(size=12))
        self.info_label.grid(row=1, column=1, sticky="w", padx=15, pady=(0, 10))

        # Progress bar (hidden for queued)
        self.progress = ctk.CTkProgressBar(self, height=8)
        self.progress.grid(row=2, column=1, sticky="ew", padx=15, pady=(0, 10))
        self.progress.set(0)

        # Status text (right side)
        status = data.get('status', 'pending')
        self.status_label = ctk.CTkLabel(self, text=status.upper(), font=ctk.CTkFont(size=11, weight="bold"))
        self.status_label.grid(row=0, column=2, padx=15, pady=10)

        # Action Buttons frame
        self.actions = ctk.CTkFrame(self, fg_color="transparent")
        self.actions.grid(row=1, column=2, rowspan=2, padx=15, pady=(0, 10))

        self._setup_state(status)

    def _setup_state(self, status):
        # Clear existing actions
        for w in self.actions.winfo_children(): w.destroy()

        if status == "downloading":
            self.progress.configure(progress_color="#1f6feb")
            ctk.CTkButton(self.actions, text="⏸", width=30, command=lambda: self.on_action(self.dl_id, "pause")).pack(side="left", padx=2)
            ctk.CTkButton(self.actions, text="⏹", width=30, fg_color="#f85149", command=lambda: self.on_action(self.dl_id, "stop")).pack(side="left", padx=2)
        
        elif status == "pending":
            self.progress.grid_remove()
            self.status_label.configure(text="QUEUED", text_color="gray")
            ctk.CTkButton(self.actions, text="↑", width=30, command=lambda: self.on_action(self.dl_id, "up")).pack(side="left", padx=2)
            ctk.CTkButton(self.actions, text="↓", width=30, command=lambda: self.on_action(self.dl_id, "down")).pack(side="left", padx=2)
            ctk.CTkButton(self.actions, text="✕", width=30, fg_color="transparent", border_width=1, command=lambda: self.on_action(self.dl_id, "remove")).pack(side="left", padx=2)
            
        elif status == "completed":
            self.progress.configure(progress_color="#3fb950")
            self.progress.set(1.0)
            self.status_label.configure(text="DONE", text_color="#3fb950")
            ctk.CTkButton(self.actions, text="📂 Open", width=60, command=lambda: self.on_action(self.dl_id, "open")).pack(side="left", padx=2)
            ctk.CTkButton(self.actions, text="🗑", width=30, fg_color="transparent", border_width=1, command=lambda: self.on_action(self.dl_id, "delete")).pack(side="left", padx=2)

        elif status == "paused":
            self.progress.configure(progress_color="#d29922")
            self.status_label.configure(text="PAUSED", text_color="#d29922")
            ctk.CTkButton(self.actions, text="▶", width=30, command=lambda: self.on_action(self.dl_id, "resume")).pack(side="left", padx=2)

    def update_progress(self, pct, info_text):
        self.progress.set(pct)
        self.info_label.configure(text=info_text)

class QueuePanel(ctk.CTkFrame):
    def __init__(self, master, on_add_click):
        super().__init__(master, fg_color=("#ffffff", "#0d1117"), corner_radius=8)
        self.on_add_click = on_add_click
        self.cards = {} # dl_id -> QueueCard

        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent")
        self.header.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(self.header, text="📥 Download Queue", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        
        ctk.CTkButton(self.header, text="+ ⬇", width=40, fg_color="#2ea043", command=self.on_add_click).pack(side="right", padx=5)
        ctk.CTkButton(self.header, text="Clear Done ✕", width=90, fg_color="transparent", border_width=1, command=self.clear_done).pack(side="right", padx=5)

        self.container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=5, pady=(0, 10))

        self.refresh()

    def refresh(self):
        items = database.db.get_active_queue()
        
        # Track existing IDs to avoid re-drawing everything (flicker)
        new_ids = [it['id'] for it in items]
        
        # Remove cards no longer in queue
        for dl_id in list(self.cards.keys()):
            if dl_id not in new_ids:
                self.cards[dl_id].destroy()
                del self.cards[dl_id]

        # Add or update cards
        for it in items:
            dl_id = it['id']
            if dl_id in self.cards:
                # Update status/info if needed
                pass
            else:
                card = QueueCard(self.container, it, self.handle_action)
                card.pack(fill="x", pady=5, padx=5)
                self.cards[dl_id] = card

    def handle_action(self, dl_id, action):
        if action == "up":
            database.db.reorder_queue(dl_id, "up")
        elif action == "down":
            database.db.reorder_queue(dl_id, "down")
        elif action == "remove":
            database.db.remove_from_queue(dl_id)
        elif action == "open":
            row = database.db.conn.execute("SELECT file_path FROM downloads WHERE id = ?", (dl_id,)).fetchone()
            if row and row['file_path']:
                os.startfile(os.path.dirname(row['file_path']))
        elif action == "delete":
            database.db.delete_download(dl_id)
        
        self.refresh()

    def clear_done(self):
        # We don't delete from DB, just hide from active queue by changing status internally 
        # (Actually the query filters by status, so we could just refresh)
        # But "Clear Done" usually implies removing them from the visual list.
        # Let's just refresh, as get_active_queue only returns active/pending.
        self.refresh()

    def update_card(self, dl_id, pct, info):
        if dl_id in self.cards:
            self.cards[dl_id].update_progress(pct, info)
