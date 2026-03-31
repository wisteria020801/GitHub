@echo off
chcp 65001 >nul
cd /d "%~dp0"
start "" python -m dashboard.app
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5000
