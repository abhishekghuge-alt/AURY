import customtkinter as ctk
import csv
import io
import zipfile
import os
from datetime import datetime
from PIL import ImageGrab, Image
from core import database

class DBReportPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Tabview for Report and ER Diagram
        self.tabs = ctk.CTkTabview(self, fg_color="transparent")
        self.tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.tab_report = self.tabs.add("📊 DB Report")
        self.tab_er = self.tabs.add("📐 ER Diagram")
        
        self._build_report_tab()
        self._build_er_tab()

    def _build_report_tab(self):
        self.scroll = ctk.CTkScrollableFrame(self.tab_report, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True)
        self.scroll.grid_columnconfigure(0, weight=1)

        self._build_sql_runner()
        self._build_preset_queries()
        self._build_schema_viewer()
        self._build_export_section()

    def _build_sql_runner(self):
        frame = ctk.CTkFrame(self.scroll, fg_color=("#f6f8fa", "#161b22"), corner_radius=8)
        frame.pack(fill="x", pady=(0, 20))
        
        lbl = ctk.CTkLabel(frame, text="🔍 Live SQL Query Runner (SELECT only)", font=ctk.CTkFont(weight="bold", size=16))
        lbl.pack(anchor="w", padx=15, pady=10)
        
        self.sql_entry = ctk.CTkTextbox(frame, height=80, font=("Consolas", 12))
        self.sql_entry.pack(fill="x", padx=15, pady=5)
        self.sql_entry.insert("1.0", "SELECT * FROM v_downloads_full LIMIT 10;")
        
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkButton(btn_frame, text="▶ Run Query", width=120, command=self._run_custom_query).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btn_frame, text="🗑 Clear", width=80, fg_color="#6e7681", command=lambda: self.sql_entry.delete("1.0", "end")).pack(side="left")

        # Results area
        self.result_frame = ctk.CTkScrollableFrame(frame, height=200, orientation="horizontal", fg_color="black")
        self.result_frame.pack(fill="x", padx=15, pady=(0, 15))
        self.result_label = ctk.CTkLabel(self.result_frame, text="Results will appear here...", text_color="gray")
        self.result_label.pack(pady=20)

    def _build_preset_queries(self):
        frame = ctk.CTkFrame(self.scroll, fg_color=("#f6f8fa", "#161b22"), corner_radius=8)
        frame.pack(fill="x", pady=(0, 20))
        
        lbl = ctk.CTkLabel(frame, text="🎓 Preset Demo Queries (College Presentation)", font=ctk.CTkFont(weight="bold", size=16))
        lbl.pack(anchor="w", padx=15, pady=10)
        
        grid_frame = ctk.CTkFrame(frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=15, pady=10)
        grid_frame.grid_columnconfigure((0, 1), weight=1)
        
        presets = [
            ("📊 Downloads per platform", "SELECT p.icon, p.name, COUNT(d.id) AS total, ROUND(SUM(d.file_size_bytes)/1e9,2) AS gb FROM platforms p LEFT JOIN downloads d ON d.platform_id = p.id GROUP BY p.id ORDER BY total DESC;"),
            ("🚀 Avg speed per session", "SELECT s.id, DATE(s.started_at) AS date, ROUND(s.avg_speed_bps/1e6,1) AS mbps, s.completed_files, s.failed_files FROM sessions s ORDER BY s.started_at DESC LIMIT 10;"),
            ("🎯 Most downloaded quality", "SELECT quality_label, COUNT(*) AS cnt, ROUND(SUM(file_size_bytes)/1e9,2) AS gb FROM downloads WHERE status='completed' GROUP BY quality_label ORDER BY cnt DESC;"),
            ("📅 Downloads per day (7d)", "SELECT DATE(downloaded_at) AS day, COUNT(*) AS total, ROUND(SUM(file_size_bytes)/1e6,1) AS mb FROM downloads WHERE downloaded_at >= DATE('now','-7 days') GROUP BY day ORDER BY day DESC;"),
            ("🔗 Full JOIN (All Data)", "SELECT d.id, d.title, p.name AS platform, d.quality_label, d.status, ROUND(d.file_size_bytes/1e6,1) AS mb, DATE(d.downloaded_at) AS date FROM downloads d JOIN platforms p ON d.platform_id = p.id JOIN sessions s ON d.session_id = s.id ORDER BY d.downloaded_at DESC LIMIT 20;"),
            ("⚡ All active triggers", "SELECT name, sql FROM sqlite_master WHERE type='trigger' ORDER BY name;"),
            ("🖼️ All views", "SELECT name, sql FROM sqlite_master WHERE type='view' ORDER BY name;"),
            ("❌ Failed downloads", "SELECT id, title, retry_count, last_error, DATE(downloaded_at) AS date FROM downloads WHERE status='failed' ORDER BY downloaded_at DESC;")
        ]
        
        for i, (name, sql) in enumerate(presets):
            btn = ctk.CTkButton(grid_frame, text=name, anchor="w", fg_color="transparent", border_width=1, 
                                command=lambda s=sql: self._run_preset(s))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky="ew")

    def _build_schema_viewer(self):
        frame = ctk.CTkFrame(self.scroll, fg_color=("#f6f8fa", "#161b22"), corner_radius=8)
        frame.pack(fill="x", pady=(0, 20))
        
        lbl = ctk.CTkLabel(frame, text="🏗️ Database Schema Viewer", font=ctk.CTkFont(weight="bold", size=16))
        lbl.pack(anchor="w", padx=15, pady=10)
        
        controls = ctk.CTkFrame(frame, fg_color="transparent")
        controls.pack(fill="x", padx=15, pady=5)
        
        self.table_var = ctk.StringVar(value="downloads")
        tables = ["downloads", "platforms", "sessions", "errors", "settings", "tags", "download_tags"]
        self.table_menu = ctk.CTkOptionMenu(controls, values=tables, variable=self.table_var, command=self._show_schema)
        self.table_menu.pack(side="left", padx=(0, 10))
        
        self.row_count_lbl = ctk.CTkLabel(controls, text="Table: downloads (0 rows)", text_color="gray")
        self.row_count_lbl.pack(side="left")
        
        self.schema_text = ctk.CTkTextbox(frame, height=150, font=("Consolas", 11), fg_color="black")
        self.schema_text.pack(fill="x", padx=15, pady=15)
        
        self._show_schema("downloads")

    def _build_export_section(self):
        btn = ctk.CTkButton(self.scroll, text="📤 Export All Tables as CSV (.zip)", fg_color="#2ea043", height=50, 
                            font=ctk.CTkFont(weight="bold"), command=self._export_all)
        btn.pack(fill="x", pady=10)
        
        self.export_status = ctk.CTkLabel(self.scroll, text="", text_color="gray")
        self.export_status.pack()

    def _build_er_tab(self):
        self.er_canvas = ctk.CTkCanvas(self.tab_er, bg="#0d1117", highlightthickness=0)
        self.er_canvas.pack(fill="both", expand=True, padx=20, pady=20)
        
        btn_save = ctk.CTkButton(self.tab_er, text="📤 Save ER Diagram as PNG", command=self._save_er_as_png)
        btn_save.pack(pady=(0, 20))
        
        self.after(200, self._draw_er_diagram)

    def _draw_er_diagram(self):
        c = self.er_canvas
        c.delete("all")
        
        # Colors
        BORDER = "#1f6feb"
        FILL = "#0d1117"
        PK_COLOR = "#f0c040"
        FK_COLOR = "#58a6ff"
        TEXT_COLOR = "#e6edf3"
        LINE_COLOR = "#8b949e"
        
        def draw_box(x, y, title, columns):
            width = 180
            line_height = 20
            height = 30 + (len(columns) * line_height) + 10
            
            # Table Rectangle
            c.create_rectangle(x, y, x+width, y+height, outline=BORDER, fill=FILL, width=2)
            # Header
            c.create_text(x + width/2, y + 15, text=title.upper(), fill=TEXT_COLOR, font=("Consolas", 11, "bold"))
            c.create_line(x, y + 30, x+width, y + 30, fill=BORDER)
            
            # Columns
            for i, (name, tag) in enumerate(columns):
                color = TEXT_COLOR
                prefix = ""
                font_style = ("Consolas", 10)
                
                if tag == "PK":
                    color = PK_COLOR
                    prefix = "🔑 "
                    font_style = ("Consolas", 10, "bold")
                elif tag == "FK":
                    color = FK_COLOR
                    prefix = "🔗 "
                    font_style = ("Consolas", 10, "italic")
                
                c.create_text(x + 10, y + 40 + (i*line_height), text=f"{prefix}{name}", fill=color, font=font_style, anchor="w")
            
            return x, y, width, height

        # Draw Tables
        s_pos = draw_box(50, 50, "sessions", [("id", "PK"), ("started_at", ""), ("ended_at", ""), ("total_files", "")])
        d_pos = draw_box(310, 50, "downloads", [("id", "PK"), ("session_id", "FK"), ("platform_id", "FK"), ("url", ""), ("title", ""), ("quality", ""), ("status", "")])
        p_pos = draw_box(570, 50, "platforms", [("id", "PK"), ("name", ""), ("domain", ""), ("icon", "")])
        
        dt_pos = draw_box(310, 250, "download_tags", [("download_id", "FK"), ("tag_id", "FK")])
        t_pos = draw_box(570, 250, "tags", [("id", "PK"), ("name", "")])
        
        # Draw Relationships
        # sessions -> downloads (1:N)
        c.create_line(s_pos[0]+s_pos[2], s_pos[1]+40, d_pos[0], d_pos[1]+60, fill=LINE_COLOR, arrow="last", width=2)
        c.create_text(s_pos[0]+s_pos[2]+20, s_pos[1]+30, text="1:N", fill=LINE_COLOR, font=("Consolas", 9))
        
        # platforms -> downloads (1:N)
        c.create_line(p_pos[0], p_pos[1]+40, d_pos[0]+d_pos[2], d_pos[1]+80, fill=LINE_COLOR, arrow="last", width=2)
        c.create_text(p_pos[0]-20, p_pos[1]+30, text="1:N", fill=LINE_COLOR, font=("Consolas", 9))
        
        # downloads -> download_tags (1:N)
        c.create_line(d_pos[0]+d_pos[2]/2, d_pos[1]+d_pos[3], dt_pos[0]+dt_pos[2]/2, dt_pos[1], fill=LINE_COLOR, arrow="last", width=2)
        c.create_text(d_pos[0]+d_pos[2]/2 + 20, d_pos[1]+d_pos[3]+20, text="1:N", fill=LINE_COLOR, font=("Consolas", 9))
        
        # tags -> download_tags (1:N)
        c.create_line(t_pos[0], t_pos[1]+40, dt_pos[0]+dt_pos[2], dt_pos[1]+50, fill=LINE_COLOR, arrow="last", width=2)
        c.create_text(t_pos[0]-20, t_pos[1]+30, text="1:N", fill=LINE_COLOR, font=("Consolas", 9))

    def _save_er_as_png(self):
        try:
            # Get canvas coordinates relative to screen
            x = self.er_canvas.winfo_rootx()
            y = self.er_canvas.winfo_rooty()
            w = self.er_canvas.winfo_width()
            h = self.er_canvas.winfo_height()
            
            # Capture and save
            img = ImageGrab.grab(bbox=(x, y, x+w, y+h))
            filename = f"er_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img.save(filename)
            
            self.export_status.configure(text=f"✅ Saved ER Diagram to {filename}", text_color="#3fb950")
            if os.name == 'nt': os.startfile(".")
        except Exception as e:
            print(f"ER Export Error: {e}")

    def _run_custom_query(self):
        sql = self.sql_entry.get("1.0", "end").strip()
        self._run_preset(sql)

    def _run_preset(self, sql):
        for child in self.result_frame.winfo_children():
            child.destroy()
            
        try:
            results = database.db.run_safe_query(sql)
            if not results:
                self.result_label = ctk.CTkLabel(self.result_frame, text="No results found.", text_color="gray")
                self.result_label.pack(pady=20)
                return
            
            # Draw table
            cols = list(results[0].keys())
            
            # Header
            header_frame = ctk.CTkFrame(self.result_frame, fg_color="#1f6feb", corner_radius=0)
            header_frame.pack(fill="x")
            for col in cols:
                ctk.CTkLabel(header_frame, text=col, width=120, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            
            # Rows
            for row in results[:50]: # Cap at 50 rows
                r_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
                r_frame.pack(fill="x")
                for col in cols:
                    val = str(row[col])
                    ctk.CTkLabel(r_frame, text=val, width=120, anchor="w").pack(side="left", padx=5)
                    
            if len(results) > 50:
                ctk.CTkLabel(self.result_frame, text=f"... and {len(results)-50} more rows", text_color="gray").pack(pady=5)
                
        except Exception as e:
            msg = f"⚠ Error: {str(e)}"
            self.result_label = ctk.CTkLabel(self.result_frame, text=msg, text_color="#ff6b6b")
            self.result_label.pack(pady=20)

    def _show_schema(self, table_name):
        self.schema_text.delete("1.0", "end")
        try:
            # PRAGMA table_info
            cols = database.db.run_safe_query(f"PRAGMA table_info({table_name})")
            fks = database.db.run_safe_query(f"PRAGMA foreign_key_list({table_name})")
            
            count_row = database.db.run_safe_query(f"SELECT COUNT(*) as c FROM {table_name}")
            self.row_count_lbl.configure(text=f"Table: {table_name} ({count_row[0]['c']} rows)")
            
            output = f"{'Column':<20} | {'Type':<10} | {'PK':<3} | {'Nullable':<8} | {'FK'}\n"
            output += "-" * 60 + "\n"
            
            for c in cols:
                name = c['name']
                ctype = c['type']
                pk = "YES" if c['pk'] else ""
                null = "NO" if c['notnull'] else "YES"
                
                fk_ref = ""
                for fk in fks:
                    if fk['from'] == name:
                        fk_ref = f"-> {fk['table']}({fk['to']})"
                
                output += f"{name:<20} | {ctype:<10} | {pk:<3} | {null:<8} | {fk_ref}\n"
            
            self.schema_text.insert("1.0", output)
        except Exception as e:
            self.schema_text.insert("1.0", f"Error fetching schema: {e}")

    def _export_all(self):
        tables = ["downloads", "platforms", "sessions", "errors", "settings", "tags", "download_tags"]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"aury_db_export_{timestamp}.zip"
        
        try:
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for table in tables:
                    results = database.db.run_safe_query(f"SELECT * FROM {table}")
                    if not results: continue
                    
                    output = io.StringIO()
                    writer = csv.DictWriter(output, fieldnames=results[0].keys())
                    writer.writeheader()
                    writer.writerows(results)
                    
                    zipf.writestr(f"{table}.csv", output.getvalue())
            
            self.export_status.configure(text=f"✅ Saved to {zip_filename}", text_color="#3fb950")
            if os.name == 'nt': os.startfile(".")
        except Exception as e:
            self.export_status.configure(text=f"❌ Export failed: {e}", text_color="#ff6b6b")
