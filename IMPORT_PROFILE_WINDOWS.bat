@echo off
setlocal
set "PYTHONUTF8=1"
chcp 65001 >nul
cd /d "%~dp0"
set "JAT_PROFILE="
set /p "JAT_PROFILE=Duong dan ho so transfer-profile-private.zip (khong kem dau ngoac kep): "
if not defined JAT_PROFILE goto :done
python -m jat_design.portable_profile --import "%JAT_PROFILE%"
:done
pause
endlocal
