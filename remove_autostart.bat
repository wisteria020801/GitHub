@echo off
chcp 65001 >nul

echo.
echo ========================================
echo   移除 GitHub Radar 开机自启
echo ========================================
echo.

schtasks /delete /tn "GitHubRadar_Dashboard" /f >nul 2>&1
schtasks /delete /tn "GitHubRadar_OpenBrowser" /f >nul 2>&1

echo   已移除开机自启任务计划
echo.
pause
