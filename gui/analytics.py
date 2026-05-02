import customtkinter as ctk
from core import database
from gui.charts import BarChart, DonutChart
from gui.widgets import StatCard

class AnalyticsTab(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        self.grid_columnconfigure((0, 1, 2), weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_top_cards()
        self._build_activity_chart()
        self._build_split_charts()

    def on_show(self):
        self.refresh_data()

    def _fmt_bytes(self, b):
        if not b: return "0 MB"
        return f"{b / (1024*1024):.1f} MB" if b < 1024**3 else f"{b / (1024**3):.1f} GB"

    def _build_top_cards(self):
        self.cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_frame.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 20))
        self.cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.card_weekly = StatCard(self.cards_frame, "📅 0", "This Week")
        self.card_weekly.grid(row=0, column=0, padx=5, sticky="ew")

        self.card_peak = StatCard(self.cards_frame, "⚡ 0 MB/s", "Peak Speed")
        self.card_peak.grid(row=0, column=1, padx=5, sticky="ew")

        self.card_avg = StatCard(self.cards_frame, "📁 0 MB", "Avg File Size")
        self.card_avg.grid(row=0, column=2, padx=5, sticky="ew")

    def _build_activity_chart(self):
        self.activity_frame = ctk.CTkFrame(self, fg_color=("#f6f8fa", "#161b22"), corner_radius=8)
        self.activity_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", pady=(0, 20))
        self.activity_frame.grid_rowconfigure(1, weight=1)
        self.activity_frame.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(self.activity_frame, text="📅 Activity — Last 14 Days", font=ctk.CTkFont(size=16, weight="bold"))
        lbl.grid(row=0, column=0, sticky="w", padx=15, pady=15)

        bg_color = "#f6f8fa" if ctk.get_appearance_mode() == "Light" else "#161b22"
        self.activity_chart = BarChart(self.activity_frame, bg=bg_color, highlightthickness=0)
        self.activity_chart.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

    def _build_split_charts(self):
        self.split_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.split_frame.grid(row=2, column=0, columnspan=3, sticky="nsew")
        self.split_frame.grid_columnconfigure((0, 1), weight=1)
        self.split_frame.grid_rowconfigure(0, weight=1)

        # Quality
        self.q_frame = ctk.CTkFrame(self.split_frame, fg_color=("#f6f8fa", "#161b22"), corner_radius=8)
        self.q_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.q_frame.grid_rowconfigure(1, weight=1)
        self.q_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.q_frame, text="🎯 Quality Split", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=15, pady=15)
        
        bg_color = "#f6f8fa" if ctk.get_appearance_mode() == "Light" else "#161b22"
        self.q_chart = DonutChart(self.q_frame, bg=bg_color, highlightthickness=0)
        self.q_chart.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

        # Platform
        self.p_frame = ctk.CTkFrame(self.split_frame, fg_color=("#f6f8fa", "#161b22"), corner_radius=8)
        self.p_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.p_frame.grid_rowconfigure(1, weight=1)
        self.p_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self.p_frame, text="🌐 Platform Split", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w", padx=15, pady=15)
        self.p_chart = DonutChart(self.p_frame, bg=bg_color, highlightthickness=0)
        self.p_chart.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

    def refresh_data(self):
        bg_color = "#f6f8fa" if ctk.get_appearance_mode() == "Light" else "#161b22"
        self.activity_chart.configure(bg=bg_color)
        self.q_chart.configure(bg=bg_color)
        self.p_chart.configure(bg=bg_color)

        # Weekly
        weekly = database.db.get_analytics_weekly()
        self.card_weekly.update_val(f"📅 {weekly['count']} dls")
        self.card_weekly.desc_label.configure(text=f"This Week ({self._fmt_bytes(weekly['bytes'])} saved)")

        # Peak
        peak = database.db.get_analytics_peak_speed()
        if peak['speed'] > 0:
            speed_mb = peak['speed'] / (1024*1024)
            date_str = peak['date'].split(" ")[0] if peak['date'] else ""
            self.card_peak.update_val(f"⚡ {speed_mb:.1f} MB/s")
            self.card_peak.desc_label.configure(text=f"Peak Speed ({date_str})")
        else:
            self.card_peak.update_val("⚡ 0 MB/s")

        # Avg File Size
        stats = database.db.get_stats()
        if stats['total_downloads'] > 0:
            avg_b = stats['total_bytes'] / stats['total_downloads']
            self.card_avg.update_val(f"📁 {self._fmt_bytes(avg_b)}")
        else:
            self.card_avg.update_val("📁 0 MB")

        # 14 Day Activity
        activity = database.db.get_analytics_activity_14d()
        if activity:
            self.activity_chart.draw(activity, color="#1f6feb" if ctk.get_appearance_mode()=="Dark" else "#0969da")

        # Quality Split
        q_data = database.db.get_analytics_quality_split()
        if q_data:
            q_colors = {"4K": "#ff6b6b", "1080p": "#1f6feb", "720p": "#3fb950", "Audio": "#d29922"}
            formatted_q = []
            for label, count in q_data:
                c = "#8b949e"
                for key in q_colors:
                    if key in label: c = q_colors[key]; break
                formatted_q.append((label, count, c))
            self.q_chart.draw(formatted_q)

        # Platform Split
        p_data = database.db.get_analytics_platform_split()
        if p_data:
            p_colors = {"YouTube": "#ff0000", "Instagram": "#e1306c", "SoundCloud": "#ff5500"}
            formatted_p = []
            for name, count, icon in p_data:
                c = p_colors.get(name, "#8b949e")
                lbl = f"{icon} {name}" if icon else name
                formatted_p.append((lbl, count, c))
            self.p_chart.draw(formatted_p)
