@echo off
setlocal
set "PYTHONUTF8=1"
chcp 65001 >nul
cd /d "%~dp0"
set "JAT_RUNTIME="
set /p "JAT_RUNTIME=Thu muc runtime cua ban bot dang dung (khong kem dau ngoac kep): "
if not defined JAT_RUNTIME goto :done
python -m jat_design.portable_profile --export "%JAT_RUNTIME%" "%~dp0runtime\transfer-profile-private.zip"
:done
pause
endlocal
