@echo off
setlocal EnableDelayedExpansion

echo ================================================
echo   AURY Desktop App Builder
echo   Target: dist\AURY.exe (single-file Windows app)
echo ================================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ first.
    pause & exit /b 1
)

REM Install build dependencies
echo.
echo [1/3] Installing build dependencies...
pip install pywebview>=4.4.1 pyinstaller>=6.0 --quiet

REM Clean previous build
if exist "build" rmdir /s /q "build"
if exist "dist\AURY.exe" del /f /q "dist\AURY.exe"

echo [2/3] Running PyInstaller...
pyinstaller ^
  --name "AURY" ^
  --onefile ^
  --windowed ^
  --icon "static\favicon.ico" ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "core;core" ^
  --hidden-import "webview" ^
  --hidden-import "webview.platforms.winforms" ^
  --hidden-import "clr" ^
  --hidden-import "flask" ^
  --hidden-import "flask_cors" ^
  --hidden-import "yt_dlp" ^
  --hidden-import "yt_dlp.extractor" ^
  --hidden-import "sqlite3" ^
  --hidden-import "engineio.async_drivers.threading" ^
  --collect-all "yt_dlp" ^
  --noconfirm ^
  desktop_app.py

echo [3/3] Checking output...
if exist "dist\AURY.exe" (
    echo.
    echo ================================================
    echo   BUILD SUCCESSFUL!
    echo   File: dist\AURY.exe
    for %%A in ("dist\AURY.exe") do echo   Size: %%~zA bytes
    echo.
    echo   Copy dist\AURY.exe anywhere — fully portable.
    echo   No Python required on the target machine.
    echo ================================================
) else (
    echo.
    echo ================================================
    echo   BUILD FAILED — check output above for errors.
    echo ================================================
)

pause
