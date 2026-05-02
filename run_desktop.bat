@echo off
REM ================================================
REM   AURY — Desktop App Launcher
REM   Double-click this to open AURY as a native window
REM ================================================

cd /d "%~dp0"

REM Set desktop mode so Google Drive download path is used
set AURY_DESKTOP=1

REM Try venv_desktop first, then generic venv, then system Python
if exist "venv_desktop\Scripts\python.exe" (
    echo Starting AURY (venv_desktop)...
    venv_desktop\Scripts\python.exe desktop_app.py
    goto :end
)

if exist "venv\Scripts\python.exe" (
    echo Starting AURY (venv)...
    venv\Scripts\python.exe desktop_app.py
    goto :end
)

python --version >nul 2>&1
if not errorlevel 1 (
    echo Starting AURY (system Python)...
    python desktop_app.py
    goto :end
)

echo ERROR: Python not found.
echo Run install_desktop.bat first to set up the environment.
pause

:end
