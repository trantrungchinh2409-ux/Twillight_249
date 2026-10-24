@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul
cd /d "%~dp0"
python -m jat_design.ai_reply --test-only --prompt "%~dp0SYSTEM_PROMPT.txt"
echo.
pause
endlocal
