@echo off
setlocal DisableDelayedExpansion
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "JAT_ZALO_CA_FILE=%~dp0certs\DigiCertGlobalRootG3.pem"
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0run_win7_python.py" goto :base_missing
if not exist "%~dp0scripts\find_python38.bat" goto :base_missing
call "%~dp0scripts\find_python38.bat"
if errorlevel 1 goto :python_failed
"%JAT_PYTHON%" -X utf8 -B "%~dp0run_agent_win7.py" --self-test
set "JAT_EXIT=%errorlevel%"
goto :done
:base_missing
set "JAT_EXIT=60"
echo Copy ALL Agent add-on files into the existing working Win7 folder. Keep runtime.
goto :done
:python_failed
set "JAT_EXIT=20"
echo Mo INSTALL_WIN7.bat de chon Python 3.8.10 x64.
:done
echo.
echo Ket qua: %JAT_EXIT%
if not defined JAT_NO_PAUSE pause
endlocal & exit /b %JAT_EXIT%
