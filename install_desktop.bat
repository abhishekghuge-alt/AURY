@echo off
setlocal EnableDelayedExpansion

echo ================================================
echo   AURY Desktop App — One-Click Installer
echo   This installs everything needed to run AURY
echo   as a native desktop window on this computer.
echo ================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10+ is required but was not found.
    echo Download from: https://www.python.org/downloads/
    pause & exit /b 1
)

echo [1/4] Creating virtual environment...
if exist "venv_desktop" (
    echo   Already exists — skipping creation.
) else (
    python -m venv venv_desktop
    if errorlevel 1 ( echo ERROR: venv creation failed. & pause & exit /b 1 )
)

echo [2/4] Activating virtual environment...
call venv_desktop\Scripts\activate.bat

echo [3/4] Installing dependencies...
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
pip install pywebview>=4.4.1 --quiet
echo   Done.

echo [4/4] Creating Desktop shortcut...
set SCRIPT="%TEMP%\AuryShortcut.vbs"
set PYTHON_EXE=%CD%\venv_desktop\Scripts\python.exe
set APP_PY=%CD%\desktop_app.py
set ICO=%CD%\static\favicon.ico

echo Set oWS = WScript.CreateObject("WScript.Shell")       > %SCRIPT%
echo sLinkFile = oWS.SpecialFolders("Desktop") ^& "\AURY.lnk" >> %SCRIPT%
echo Set oLink = oWS.CreateShortcut(sLinkFile)             >> %SCRIPT%
echo oLink.TargetPath = "%PYTHON_EXE%"                     >> %SCRIPT%
echo oLink.Arguments = "%APP_PY%"                          >> %SCRIPT%
echo oLink.WorkingDirectory = "%CD%"                       >> %SCRIPT%
echo oLink.Description = "AURY Smart Media Downloader"     >> %SCRIPT%
echo oLink.IconLocation = "%ICO%"                          >> %SCRIPT%
echo oLink.Save                                            >> %SCRIPT%
cscript /nologo %SCRIPT%
del %SCRIPT% >nul 2>&1

echo.
echo ================================================
echo   INSTALLATION COMPLETE!
echo.
echo   To launch AURY:
echo     Option A: Double-click "AURY" on your Desktop
echo     Option B: Double-click run_desktop.bat
echo     Option C: python desktop_app.py
echo.
echo   On first launch, go to Settings and set your
echo   Google Drive download folder.
echo ================================================
pause
