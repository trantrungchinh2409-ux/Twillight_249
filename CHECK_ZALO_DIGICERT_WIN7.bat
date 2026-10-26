@echo off
setlocal DisableDelayedExpansion
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
call "%~dp0scripts\find_python38.bat"
if not errorlevel 1 goto :run
echo Nhap duong dan Python 3.8.10 x64 python.exe. Khong nhap token/key.
set "JAT_PYTHON="
set /p "JAT_PYTHON=Python: "
if not defined JAT_PYTHON goto :failed
call "%~dp0scripts\find_python38.bat"
if errorlevel 1 goto :failed
:run
"%JAT_PYTHON%" -X utf8 -B "%~dp0check_zalo_digicert.py"
set "JAT_EXIT=%errorlevel%"
goto :done
:failed
set "JAT_EXIT=20"
echo FAIL: Python 3.8.10 x64 chua duoc tim thay. Khong doi he thong.
:done
echo Exit=%JAT_EXIT%
echo Exit 0=private TLS and process-context tests PASS; 1=FAIL; 2=TLS PASS but integration test FAIL.
if not defined JAT_NO_PAUSE pause
endlocal & exit /b %JAT_EXIT%
