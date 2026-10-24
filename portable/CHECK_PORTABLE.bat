@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul
cd /d "%~dp0"
"%~dp0JATDesign.exe" --self-test
if errorlevel 1 goto :done
"%~dp0JATDesign.exe" --check-https
:done
echo.
pause
endlocal
