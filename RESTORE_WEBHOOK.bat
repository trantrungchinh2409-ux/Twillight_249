@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul
cd /d "%~dp0"
python -m jat_design.webhook_switch --restore
echo.
pause
endlocal
