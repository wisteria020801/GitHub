@echo off
chcp 65001 >nul

set "VBS_PATH=%~dp0start_dashboard_silent.vbs"
set "SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\GitHubRadar.lnk"

powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = '%VBS_PATH%'; $s.WorkingDirectory = '%~dp0'; $s.Description = 'GitHub Radar Dashboard'; $s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo SUCCESS: Autostart configured!
    echo Shortcut: %SHORTCUT_PATH%
) else (
    echo FAILED: Please create shortcut manually
)

pause
