@echo off
title AURY Installer
echo.
echo  ██████╗  ██╗   ██╗ ██████╗  ██╗   ██╗
echo  ██╔══██╗ ██║   ██║ ██╔══██╗ ╚██╗ ██╔╝
echo  ███████║ ██║   ██║ ██████╔╝  ╚████╔╝ 
echo  ██╔══██║ ██║   ██║ ██╔══██╗   ╚██╔╝  
echo  ██║  ██║ ╚██████╔╝ ██║  ██║    ██║   
echo  ╚═╝  ╚═╝  ╚═════╝  ╚═╝  ╚═╝    ╚═╝   
echo.
echo  AURY Smart Media Downloader
echo  Installing dependencies...
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Install from python.org
    pause
    exit /b 1
)

REM Create venv
echo  [1/4] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

REM Install requirements
echo  [2/4] Installing Python packages...
pip install -r requirements.txt --quiet

REM Check aria2c
echo  [3/4] Checking aria2c...
where aria2c >nul 2>&1
if errorlevel 1 (
    echo  [INFO] aria2c not found.
    echo  [INFO] Download from: https://github.com/aria2/aria2/releases
    echo  [INFO] Add to PATH for 3x faster downloads.
) else (
    echo  [OK] aria2c found - Turbo mode enabled
)

REM Create desktop shortcut
echo  [4/4] Creating shortcuts...
python -c "
import os, sys
desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
shortcut = os.path.join(desktop, 'AURY.bat')
venv_python = os.path.join(os.getcwd(), 'venv', 'Scripts', 'python.exe')
with open(shortcut, 'w') as f:
    f.write(f'@echo off\ncd /d \"{os.getcwd()}\"\n')
    f.write(f'call venv\\Scripts\\activate.bat\n')
    f.write(f'python gui_main.py\n')
print('Desktop shortcut created: AURY.bat')
"

echo.
echo  ╔══════════════════════════════════════╗
echo  ║  AURY installed successfully!        ║
echo  ║  Launching GUI...                    ║
echo  ╚══════════════════════════════════════╝
echo.
python gui_main.py
