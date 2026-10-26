@echo off
setlocal DisableDelayedExpansion
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0scripts\find_python38.bat"
if errorlevel 1 goto :failed
"%JAT_PYTHON%" -X utf8 -B "%~dp0run_win7_python.py"
set "JAT_EXIT=%errorlevel%"
goto :done
:failed
set "JAT_EXIT=20"
echo Mo INSTALL_WIN7.bat truoc. Khong khoi dong EXE cu.
:done
echo.
echo Ket qua: %JAT_EXIT%
if not defined JAT_NO_PAUSE pause
endlocal & exit /b %JAT_EXIT%
