@echo off
chcp 65001 > nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
.venv\Scripts\python.exe main.py
if %errorlevel% neq 0 pause
