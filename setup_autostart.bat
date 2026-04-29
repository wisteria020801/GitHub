@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: 创建开机自启任务计划
schtasks /create /tn "GitHubRadar_Dashboard" /tr "python -m dashboard.app" /sc onlogon /rl limited /f >nul 2>&1
schtasks /create /tn "GitHubRadar_OpenBrowser" /tr "cmd /c start http://127.0.0.1:5000" /sc onlogon /rl limited /delay 0000:05 /f >nul 2>&1

echo.
echo ========================================
echo   GitHub Radar Dashboard 开机自启设置
echo ========================================
echo.
echo   已创建以下任务计划：
echo   1. GitHubRadar_Dashboard - 登录后自动启动Dashboard
echo   2. GitHubRadar_OpenBrowser - 登录5秒后自动打开浏览器
echo.
echo   现在启动 Dashboard...
echo.

start "" python -m dashboard.app
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5000
