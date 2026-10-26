@echo off
setlocal DisableDelayedExpansion
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
call "%~dp0scripts\find_python38.bat"
if not errorlevel 1 goto :run
echo Chon Python 3.8.10 x64 python.exe da cai. Khong can token.
set "JAT_PYTHON="
set /p "JAT_PYTHON=Python: "
if not defined JAT_PYTHON goto :failed
call "%~dp0scripts\find_python38.bat"
if errorlevel 1 goto :failed
:run
"%JAT_PYTHON%" -X utf8 -B "%~dp0zalo_cert_check.py"
set "JAT_EXIT=%errorlevel%"
goto :done
:failed
set "JAT_EXIT=20"
echo FAIL: Khong tim thay Python 3.8.10 x64. Khong doi cau hinh may.
:done
echo Exit=%JAT_EXIT%
echo Exit 0=default TLS PASS; 2=only approved CA test PASS, bot not changed; 1=FAIL.
if not defined JAT_NO_PAUSE pause
endlocal & exit /b %JAT_EXIT%
