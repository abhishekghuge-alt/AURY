import os
import sys
import threading
import time
from pathlib import Path
import pystray
from PIL import Image, ImageDraw

# Fix Tcl/Tk environment
if sys.platform == "win32":
    system_python_path = Path(r"C:\Users\DAR AL WEFAQ\AppData\Local\Programs\Python\Python312")
    tcl_dir = system_python_path / "tcl"
    
    if tcl_dir.exists():
        os.environ['TCL_LIBRARY'] = str(tcl_dir / "tcl8.6")
        os.environ['TK_LIBRARY'] = str(tcl_dir / "tk8.6")
        os.environ['PATH'] = str(tcl_dir / "tcl8.6") + os.pathsep + str(tcl_dir / "tk8.6") + os.pathsep + os.environ.get('PATH', '')

# Ensure AURY root is in PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.resolve()))

try:
    from gui.app import AuryApp
    from core import database
except Exception as e:
    print(f"Error importing AuryApp: {e}")
    sys.exit(1)

def create_tray_icon(app):
    # Draw simple icon
    img = Image.new("RGB", (64,64), color="#0d1117")
    draw = ImageDraw.Draw(img)
    draw.ellipse([8,8,56,56], fill="#1f6feb")
    
    def on_open():
        app.after(0, app.deiconify())
        app.after(0, app.focus_force())

    def on_quit():
        app.after(0, app.quit_app)

    def get_menu():
        # Get active download count from DB
        try:
            active = database.db.run_safe_query("SELECT COUNT(*) as c FROM downloads WHERE status='downloading' OR status='pending'")
            n = active[0]['c'] if active else 0
        except:
            n = 0
            
        return pystray.Menu(
            pystray.MenuItem(f"AURY ({n} Active)", on_open, default=True),
            pystray.MenuItem(f"⬇ {n} active downloads", None, enabled=False),
            pystray.MenuItem("─────────", None, enabled=False),
            pystray.MenuItem("Open AURY", on_open),
            pystray.MenuItem("New Download", lambda: app.after(0, lambda: app.show_page("dashboard") or app.pages["dashboard"].open_download_modal())),
            pystray.MenuItem("Quit", on_quit),
        )

    icon = pystray.Icon("AURY", img, "AURY Downloader", get_menu())
    
    def update_loop():
        while icon.visible:
            time.sleep(2)
            icon.menu = get_menu()
            
    threading.Thread(target=update_loop, daemon=True).start()
    return icon

def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00000080)
        except Exception: pass

    try:
        app = AuryApp()
        
        # Setup Tray
        tray = create_tray_icon(app)
        app.set_tray_icon(tray)
        
        # Run tray in separate thread
        threading.Thread(target=tray.run, daemon=True).start()
        
        app.mainloop()
    except Exception as e:
        print(f"Aury GUI encountered an error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
