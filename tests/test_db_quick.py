import sys, shutil, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
LIVE = Path(__file__).parent.parent / "aury.db"
TEST = Path(tempfile.gettempdir()) / "aury_test_copy.db"
print("Live DB exists:", LIVE.exists())
if LIVE.exists():
    try:
        shutil.copy2(LIVE, TEST)
        print("Copied OK to:", TEST)
    except Exception as e:
        print("Copy FAILED:", e)
        TEST = LIVE
import core.config as c
c.DATABASE_PATH = TEST
print("Patched DATABASE_PATH to:", c.DATABASE_PATH)
from core.database import AuryDB
print("Connecting to DB...")
db = AuryDB(TEST)
print("Connected! Tables:", [r["name"] for r in db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()])
