@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
echo Close the Agent window first. This uses the same runtime, vault, counters and guards.
echo No files or databases will be deleted. The original accepted Python runner will start.
call "%~dp0START_WIN7_PYTHON.bat"
set "JAT_EXIT=%errorlevel%"
endlocal & exit /b %JAT_EXIT%
