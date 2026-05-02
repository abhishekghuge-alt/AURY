@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
:: Run using the fast venv path directly
.venv\Scripts\python.exe main.py
if %errorlevel% neq 0 pause
