"""Root entry point — allows running with: python main.py"""
import sys
import os
import subprocess

# --- Portability Check ---
# On some Windows systems, the default 'python.exe' is a stub that opens the MS Store.
# REAL_PYTHON points to the actual installation to avoid crashes.
# For portability, this is now optional.
REAL_PYTHON = os.environ.get("AURY_PYTHON_PATH", r"C:\Users\DAR AL WEFAQ\AppData\Local\Programs\Python\Python312\python.exe")

def check_and_relaunch():
    # If we are running in the broken C:\WINDOWS\python.exe stub, try to relaunch with the real one
    if "WINDOWS" in sys.executable.upper() and os.path.exists(REAL_PYTHON):
        if os.environ.get("AURY_LAUNCHED") != "1":
            env = os.environ.copy()
            env["AURY_LAUNCHED"] = "1"
            env["PYTHONUTF8"] = "1" 
            try:
                subprocess.run([REAL_PYTHON, __file__] + sys.argv[1:], env=env)
                sys.exit(0)
            except Exception:
                pass # Fallback to current executable if relaunch fails

if __name__ == "__main__":
    check_and_relaunch()
    
    # Import and run the actual main function
    try:
        from cli.main import main
        main()
    except ImportError:
        print("Error: Could not find dependencies. Please run with the ( shortcut first.")
