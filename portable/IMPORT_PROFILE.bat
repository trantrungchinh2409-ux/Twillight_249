@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul
cd /d "%~dp0"
set "JAT_PROFILE="
set /p "JAT_PROFILE=Duong dan day du toi transfer-profile-private.zip: "
if not defined JAT_PROFILE goto :done
"%~dp0JATDesign.exe" --import-profile "%JAT_PROFILE%"
:done
echo.
pause
endlocal
