import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from core.config import DATABASE_PATH

class AuryDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._lock = threading.RLock()
        
        # Connect to DB
        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        self.conn.row_factory = sqlite3.Row
        
        # Enable WAL and foreign keys
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        
        with self._lock:
            self._migrate_old_schema()
            self._migrate_v1b_schema()
            self._create_schema()
            self._seed_platforms()
            self._migrate_queue_pos()
            self.sync_config_with_db()

    def sync_config_with_db(self):
        """Phase 1B/V2: Inject DB settings into core.config at runtime."""
        from core import config
        
        # Download Folder
        df = self.get_setting("download_dir")
        if df:
            config.DOWNLOAD_DIR = Path(df)
            # We don't auto-create here to avoid permission issues at startup
            # but we assume the user sets a valid path.
        
        # Max Workers
        mw = self.get_setting("max_workers")
        if mw: 
            try: config.MAX_WORKERS = int(mw)
            except: pass
            
        # Default Quality
        dq = self.get_setting("default_quality")
        if dq: config.DEFAULT_QUALITY_KEY = str(dq)

    def _migrate_old_schema(self):
        """Renames old V1 tables to backups to start fresh."""
        try:
            # Check if old downloads table exists (without platform_id)
            cursor = self.conn.execute("PRAGMA table_info(downloads)")
            columns = [row['name'] for row in cursor.fetchall()]
            
            if columns and 'platform_id' not in columns:
                # This is the old schema. Rename tables.
                self.conn.execute("ALTER TABLE downloads RENAME TO downloads_backup")
                
                # Check and rename sessions if needed
                cursor = self.conn.execute("PRAGMA table_info(sessions)")
                if cursor.fetchall():
                    self.conn.execute("ALTER TABLE sessions RENAME TO sessions_backup")
                
                # Check and rename errors if needed
                cursor = self.conn.execute("PRAGMA table_info(errors)")
                if cursor.fetchall():
                    self.conn.execute("ALTER TABLE errors RENAME TO errors_backup")
                    
                self.conn.commit()
        except sqlite3.OperationalError:
            pass # Table might not exist or rename failed

    def _migrate_v1b_schema(self):
        """Phase 1B: Add url_original."""
        try:
            self.conn.execute("ALTER TABLE downloads ADD COLUMN url_original TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # already exists

    def _migrate_queue_pos(self):
        """Phase 3: Add queue_position for GUI Smart Queue."""
        try:
            self.conn.execute("ALTER TABLE downloads ADD COLUMN queue_position INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass # already exists

    def _create_schema(self):
        with self.conn:
            # Table 1: platforms
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS platforms (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL UNIQUE,
                    icon        TEXT,
                    domain      TEXT,
                    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table 2: sessions
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ended_at        DATETIME,
                    total_files     INTEGER DEFAULT 0,
                    completed_files INTEGER DEFAULT 0,
                    failed_files    INTEGER DEFAULT 0,
                    total_bytes     INTEGER DEFAULT 0,
                    avg_speed_bps   REAL DEFAULT 0,
                    peak_speed_bps  REAL DEFAULT 0,
                    duration_secs   REAL DEFAULT 0,
                    scheduled_time  TEXT
                )
            """)
            
            # Table 3: downloads
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id        INTEGER REFERENCES sessions(id) ON DELETE SET NULL,
                    platform_id       INTEGER REFERENCES platforms(id) ON DELETE SET NULL,
                    url               TEXT NOT NULL,
                    url_original      TEXT,
                    title             TEXT,
                    quality_label     TEXT,
                    quality_format    TEXT,
                    status            TEXT DEFAULT 'pending',
                    file_path         TEXT,
                    file_size_bytes   INTEGER DEFAULT 0,
                    duration_secs     REAL DEFAULT 0,
                    avg_speed_bps     REAL DEFAULT 0,
                    peak_speed_bps    REAL DEFAULT 0,
                    subtitles_lang    TEXT,
                    subtitles_path    TEXT,
                    thumbnail_path    TEXT,
                    retry_count       INTEGER DEFAULT 0,
                    last_error        TEXT,
                    scheduled_at      DATETIME,
                    downloaded_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_quick_mode     BOOLEAN DEFAULT 0,
                    is_redownload     BOOLEAN DEFAULT 0
                )
            """)
            
            # Table 4: settings
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key         TEXT PRIMARY KEY,
                    value       TEXT NOT NULL,
                    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table 5: tags and download_tags
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    name  TEXT NOT NULL UNIQUE
                )
            """)
            
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS download_tags (
                    download_id  INTEGER REFERENCES downloads(id) ON DELETE CASCADE,
                    tag_id       INTEGER REFERENCES tags(id) ON DELETE CASCADE,
                    PRIMARY KEY (download_id, tag_id)
                )
            """)

            # Indexes
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_downloads_platform ON downloads(platform_id)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_downloads_date ON downloads(downloaded_at)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_downloads_session ON downloads(session_id)")

            # Views
            self.conn.execute("""
                CREATE VIEW IF NOT EXISTS v_downloads_full AS
                SELECT
                    d.id, d.session_id, d.title, d.url, d.quality_label, d.status,
                    d.file_size_bytes, d.duration_secs, d.downloaded_at, d.file_path,
                    d.subtitles_lang, d.subtitles_path, d.is_quick_mode,
                    p.name AS platform, p.icon AS platform_icon,
                    s.started_at AS session_start
                FROM downloads d
                LEFT JOIN platforms p ON d.platform_id = p.id
                LEFT JOIN sessions s  ON d.session_id  = s.id
            """)
            
            self.conn.execute("""
                CREATE VIEW IF NOT EXISTS v_platform_stats AS
                SELECT
                    p.name, p.icon,
                    COUNT(d.id)              AS total_downloads,
                    SUM(d.file_size_bytes)   AS total_bytes,
                    AVG(d.avg_speed_bps)     AS avg_speed,
                    SUM(CASE WHEN d.status='completed' THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN d.status='failed'    THEN 1 ELSE 0 END) AS failed
                FROM platforms p
                LEFT JOIN downloads d ON d.platform_id = p.id
                GROUP BY p.id
            """)
            
            self.conn.execute("""
                CREATE VIEW IF NOT EXISTS v_daily_activity AS
                SELECT
                    DATE(downloaded_at)      AS day,
                    COUNT(*)                 AS downloads,
                    SUM(file_size_bytes)     AS total_bytes,
                    AVG(avg_speed_bps)       AS avg_speed
                FROM downloads
                WHERE status = 'completed'
                GROUP BY DATE(downloaded_at)
                ORDER BY day DESC
            """)

            # Triggers
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_update_session_on_complete
                AFTER UPDATE OF status ON downloads
                WHEN NEW.status = 'completed'
                BEGIN
                    UPDATE sessions SET
                        completed_files = completed_files + 1,
                        total_bytes = total_bytes + NEW.file_size_bytes
                    WHERE id = NEW.session_id;
                END;
            """)
            
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_update_session_on_fail
                AFTER UPDATE OF status ON downloads
                WHEN NEW.status = 'failed'
                BEGIN
                    UPDATE sessions SET
                        failed_files = failed_files + 1
                    WHERE id = NEW.session_id;
                END;
            """)
            
            self.conn.execute("""
                CREATE TRIGGER IF NOT EXISTS trg_settings_updated
                AFTER UPDATE ON settings
                BEGIN
                    UPDATE settings SET updated_at = CURRENT_TIMESTAMP
                    WHERE key = NEW.key;
                END;
            """)

    def _seed_platforms(self):
        platforms = [
            ("YouTube", "🎥", "youtube.com"),
            ("YouTube (Short)", "📱", "youtu.be"),
            ("Instagram", "📸", "instagram.com"),
            ("TikTok", "🎵", "tiktok.com"),
            ("Twitter", "🐦", "twitter.com"),
            ("X", "🐦", "x.com"),
            ("Facebook", "📘", "facebook.com"),
            ("Reddit", "👽", "reddit.com"),
            ("Vimeo", "📼", "vimeo.com"),
            ("Twitch", "🎮", "twitch.tv"),
            ("SoundCloud", "🎧", "soundcloud.com")
        ]
        with self.conn:
            for name, icon, domain in platforms:
                self.conn.execute(
                    "INSERT OR IGNORE INTO platforms (name, icon, domain) VALUES (?, ?, ?)",
                    (name, icon, domain)
                )

    def get_platform_id(self, url: str) -> int:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
            
        with self._lock:
            # Exact match first
            cursor = self.conn.execute("SELECT id FROM platforms WHERE domain = ?", (domain,))
            row = cursor.fetchone()
            if row: return row['id']
            
            # Partial match (e.g., handles m.youtube.com matching youtube.com)
            cursor = self.conn.execute("SELECT id, domain FROM platforms")
            for row in cursor.fetchall():
                if row['domain'] in domain:
                    return row['id']
                    
            return None

    # --- Session Methods ---

    def start_session(self, scheduled_time=None) -> int:
        with self._lock, self.conn:
            now = datetime.now().isoformat()
            cursor = self.conn.execute(
                "INSERT INTO sessions (started_at, scheduled_time) VALUES (?, ?)", 
                (now, scheduled_time)
            )
            return cursor.lastrowid

    def end_session(self, session_id: int):
        with self._lock, self.conn:
            now = datetime.now().isoformat()
            self.conn.execute("UPDATE sessions SET ended_at = ? WHERE id = ?", (now, session_id))

    def get_last_session_id(self) -> int:
        with self._lock:
            cursor = self.conn.execute("SELECT id FROM sessions ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            return int(row['id']) if row else 0

    def get_session_summary(self, session_id: int) -> dict:
        with self._lock:
            cursor = self.conn.execute(
                """
                SELECT
                    SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) AS completed,
                    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) AS failed,
                    SUM(CASE WHEN status='stopped' THEN 1 ELSE 0 END) AS stopped,
                    COALESCE(SUM(file_size_bytes), 0) AS total_bytes,
                    COALESCE(SUM(duration_secs), 0) AS total_duration
                FROM downloads
                WHERE session_id = ?
                """,
                (session_id,)
            )
            row = cursor.fetchone()
            if not row:
                return {"completed": 0, "failed": 0, "stopped": 0, "total_bytes": 0, "total_duration": 0.0}
            return {
                "completed": int(row['completed'] or 0),
                "failed": int(row['failed'] or 0),
                "stopped": int(row['stopped'] or 0),
                "total_bytes": int(row['total_bytes'] or 0),
                "total_duration": float(row['total_duration'] or 0.0),
            }

    def get_session_downloads(self, session_id: int) -> list[dict]:
        with self._lock:
            cursor = self.conn.execute(
                "SELECT * FROM v_downloads_full WHERE session_id = ? ORDER BY id ASC", 
                (session_id,)
            )
            return [dict(r) for r in cursor.fetchall()]

    # --- Download Methods ---

    def insert_download(self, data: dict) -> int:
        """Inserts a download record.
        Keys expected: session_id, url, title, quality_label, quality_format, is_redownload, subtitles_lang, status
        """
        if 'url' in data and 'platform_id' not in data:
            data['platform_id'] = self.get_platform_id(data['url'])
            
        if 'url' in data and 'url_original' not in data:
            data['url_original'] = data['url']
            
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        values = tuple(data.values())
        
        with self._lock, self.conn:
            cursor = self.conn.execute(
                f"INSERT INTO downloads ({columns}) VALUES ({placeholders})", 
                values
            )
            return cursor.lastrowid

    def update_status(self, dl_id: int, status: str, **kwargs):
        """Updates download status and other fields."""
        kwargs['status'] = status
        set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = tuple(kwargs.values()) + (dl_id,)
        
        with self._lock, self.conn:
            self.conn.execute(
                f"UPDATE downloads SET {set_clause} WHERE id = ?", 
                values
            )

    def update_download_title(self, dl_id: int, title: str):
        with self._lock, self.conn:
            self.conn.execute("UPDATE downloads SET title = ? WHERE id = ?", (title, dl_id))

    def increment_retry(self, dl_id: int):
        with self._lock, self.conn:
            self.conn.execute("UPDATE downloads SET retry_count = retry_count + 1 WHERE id = ?", (dl_id,))

    def log_error(self, dl_id: int, error_msg: str):
        with self._lock, self.conn:
            self.conn.execute("UPDATE downloads SET last_error = ? WHERE id = ?", (error_msg, dl_id))

    def check_duplicate(self, url: str) -> str:
        """Checks if a URL has already been downloaded successfully."""
        with self._lock:
            cursor = self.conn.execute(
                "SELECT downloaded_at FROM downloads WHERE url = ? AND status = 'completed' ORDER BY id DESC LIMIT 1",
                (url,)
            )
            row = cursor.fetchone()
            return row['downloaded_at'] if row else None

    # --- History & Stats ---

    def get_active_queue(self) -> list[dict]:
        """Returns pending, downloading, and paused items for the GUI QueuePanel."""
        with self._lock:
            cursor = self.conn.execute("""
                SELECT * FROM v_downloads_full 
                WHERE status IN ('pending', 'downloading', 'paused', 'retrying')
                ORDER BY queue_position ASC, id ASC
            """)
            return [dict(r) for r in cursor.fetchall()]

    def reorder_queue(self, dl_id: int, direction: str):
        """direction: 'up' or 'down'"""
        with self._lock, self.conn:
            cursor = self.conn.execute("SELECT queue_position FROM downloads WHERE id = ?", (dl_id,))
            row = cursor.fetchone()
            if not row: return
            
            curr_pos = row['queue_position']
            new_pos = curr_pos - 1 if direction == 'up' else curr_pos + 1
            if new_pos < 0: new_pos = 0
            
            # Swap with whatever is at new_pos
            self.conn.execute("UPDATE downloads SET queue_position = ? WHERE queue_position = ?", (curr_pos, new_pos))
            self.conn.execute("UPDATE downloads SET queue_position = ? WHERE id = ?", (new_pos, dl_id))

    def remove_from_queue(self, dl_id: int):
        with self._lock, self.conn:
            self.conn.execute("DELETE FROM downloads WHERE id = ? AND status = 'pending'", (dl_id,))

    def get_history(self, limit: int = 100) -> list[dict]:
        """Simple wrapper — returns latest downloads for dashboards and history pages."""
        return self.get_filtered_history(limit=limit)

    def get_filtered_history(self, search="", platform="All", status="All", sort="Newest", limit=15, offset=0) -> list[dict]:
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append("(title LIKE ? OR url LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        if platform != "All":
            where_clauses.append("platform = ?")
            params.append(platform)
            
        if status != "All":
            where_clauses.append("status = ?")
            params.append(status.lower())
            
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        sort_sql = "id DESC"
        if sort == "Oldest": sort_sql = "id ASC"
        elif sort == "Largest": sort_sql = "file_size_bytes DESC"
        elif sort == "Fastest": sort_sql = "avg_speed_bps DESC"
        
        sql = f"SELECT * FROM v_downloads_full {where_sql} ORDER BY {sort_sql} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._lock:
            cursor = self.conn.execute(sql, params)
            return [dict(r) for r in cursor.fetchall()]

    def get_history_count(self, search="", platform="All", status="All") -> int:
        where_clauses = []
        params = []
        
        if search:
            where_clauses.append("(title LIKE ? OR url LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        if platform != "All":
            where_clauses.append("platform = ?")
            params.append(platform)
            
        if status != "All":
            where_clauses.append("status = ?")
            params.append(status.lower())
            
        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        sql = f"SELECT COUNT(*) as c FROM v_downloads_full {where_sql}"
        
        with self._lock:
            cursor = self.conn.execute(sql, params)
            row = cursor.fetchone()
            return row['c'] if row else 0

    def get_history_platforms(self) -> list[str]:
        with self._lock:
            cursor = self.conn.execute("SELECT DISTINCT platform FROM v_downloads_full WHERE platform IS NOT NULL")
            return [r['platform'] for r in cursor.fetchall()]

    def delete_download(self, dl_id: int):
        with self._lock, self.conn:
            self.conn.execute("DELETE FROM downloads WHERE id = ?", (dl_id,))

    def clear_all_history(self) -> int:
        with self._lock:
            cursor = self.conn.execute("SELECT COUNT(*) as c FROM downloads")
            count = cursor.fetchone()['c'] or 0
            with self.conn:
                self.conn.execute("DELETE FROM downloads")
                self.conn.execute("DELETE FROM sessions")
            self.conn.execute("VACUUM")
            return count

    def get_advanced_stats(self) -> dict:
        """Returns complex stats for the Settings DBMS showcase."""
        with self._lock:
            # File size
            cursor = self.conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor = self.conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            db_size_bytes = page_count * page_size
            
            # Total records
            cursor = self.conn.execute("SELECT COUNT(*) as c FROM downloads")
            total_dl = cursor.fetchone()['c'] or 0
            cursor = self.conn.execute("SELECT COUNT(*) as c FROM sessions")
            total_sessions = cursor.fetchone()['c'] or 0
            
            # Top platforms
            cursor = self.conn.execute("""
                SELECT p.name AS platform, COUNT(d.id) AS c, SUM(d.file_size_bytes) AS s
                FROM downloads d
                JOIN platforms p ON d.platform_id = p.id
                WHERE d.status = 'completed'
                GROUP BY d.platform_id
                ORDER BY c DESC LIMIT 3
            """)
            top_platforms = [dict(r) for r in cursor.fetchall()]
            
            # Top quality
            cursor = self.conn.execute("""
                SELECT quality_label, COUNT(id) AS c
                FROM downloads
                GROUP BY quality_label
                ORDER BY c DESC LIMIT 3
            """)
            top_quality = [dict(r) for r in cursor.fetchall()]
            
            # Averages and extremes
            cursor = self.conn.execute("SELECT AVG(avg_speed_bps) as a FROM sessions")
            avg_speed_bps = cursor.fetchone()['a'] or 0.0
            
            cursor = self.conn.execute("""
                SELECT file_size_bytes, title, downloaded_at, avg_speed_bps
                FROM downloads
                WHERE status = 'completed'
            """)
            rows = cursor.fetchall()
            largest_dl = max(rows, key=lambda r: r['file_size_bytes']) if rows else None
            fastest_dl = max(rows, key=lambda r: r['avg_speed_bps']) if rows else None
            
            return {
                "db_size_bytes": db_size_bytes,
                "total_dl": total_dl,
                "total_sessions": total_sessions,
                "top_platforms": top_platforms,
                "top_quality": top_quality,
                "avg_speed_bps": avg_speed_bps,
                "largest_dl": dict(largest_dl) if largest_dl else None,
                "fastest_dl": dict(fastest_dl) if fastest_dl else None
            }

    def get_stats(self) -> dict:
        """Returns application lifetime statistics."""
        with self._lock:
            cursor = self.conn.execute("SELECT COUNT(*) as c FROM downloads WHERE status = 'completed'")
            total_dl = cursor.fetchone()['c'] or 0
            
            cursor = self.conn.execute("SELECT COUNT(*) as c FROM sessions")
            total_sessions = cursor.fetchone()['c'] or 0
            
            cursor = self.conn.execute("SELECT SUM(file_size_bytes) as s FROM downloads WHERE status = 'completed'")
            total_bytes = cursor.fetchone()['s'] or 0
            
            return {
                "total_downloads": total_dl,
                "total_sessions": total_sessions,
                "total_bytes": total_bytes
            }

    # --- Settings ---
    
    def get_setting(self, key: str, default=None) -> str:
        with self._lock:
            cursor = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else default
            
    def set_setting(self, key: str, value: str):
        with self._lock, self.conn:
            self.conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
                (key, value, value)
            )


    def get_analytics_weekly(self) -> dict:
        with self._lock:
            cursor = self.conn.execute("""
                SELECT COUNT(*) as c, SUM(file_size_bytes) as s
                FROM downloads
                WHERE downloaded_at >= date('now', '-7 days')
                  AND status='completed'
            """)
            row = cursor.fetchone()
            return {"count": row['c'] or 0, "bytes": row['s'] or 0}

    def get_analytics_peak_speed(self) -> dict:
        with self._lock:
            cursor = self.conn.execute("""
                SELECT MAX(avg_speed_bps) as speed, title, downloaded_at
                FROM downloads WHERE status='completed'
            """)
            row = cursor.fetchone()
            return {"speed": row['speed'] or 0, "title": row['title'] or "Unknown", "date": row['downloaded_at']}

    def get_analytics_activity_14d(self) -> list[tuple[str, int]]:
        with self._lock:
            cursor = self.conn.execute("""
                SELECT date(downloaded_at) AS day, COUNT(*) as c
                FROM downloads
                WHERE downloaded_at >= date('now', '-14 days')
                GROUP BY day ORDER BY day
            """)
            return [(r['day'], r['c']) for r in cursor.fetchall()]

    def get_analytics_quality_split(self) -> list[tuple[str, int]]:
        with self._lock:
            cursor = self.conn.execute("""
                SELECT quality_label, COUNT(*) as c FROM downloads
                WHERE status='completed' GROUP BY quality_label
            """)
            return [(r['quality_label'] or 'Unknown', r['c']) for r in cursor.fetchall()]

    def get_analytics_platform_split(self) -> list[tuple[str, int, str]]:
        with self._lock:
            cursor = self.conn.execute("""
                SELECT p.name, COUNT(*) as c, p.icon 
                FROM platforms p
                LEFT JOIN downloads d ON d.platform_id = p.id
                WHERE d.status='completed' 
                GROUP BY p.id
            """)
            return [(r['name'], r['c'], r['icon']) for r in cursor.fetchall()]


    def run_safe_query(self, sql: str) -> list[dict]:
        """Runs a SELECT-only query for reporting purposes."""
        s = sql.strip().upper()
        if not s.startswith("SELECT") and not s.startswith("PRAGMA") and not s.startswith("WITH"):
            raise ValueError("Only SELECT queries are allowed for safety.")
        
        with self._lock:
            cursor = self.conn.execute(sql)
            return [dict(r) for r in cursor.fetchall()]

# Global Database Instance (Lazy Loaded)
_db = None

def get_db():
    global _db
    if _db is None:
        _db = AuryDB(DATABASE_PATH)
    return _db

# For backward compatibility with existing code
class _LazyDB:
    def __getattr__(self, name):
        return getattr(get_db(), name)

db = _LazyDB()

