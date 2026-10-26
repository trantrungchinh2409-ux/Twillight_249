@echo off
rem Called by launchers with SETLOCAL; exports JAT_PYTHON only to that caller.
rem Delayed expansion must stay disabled so paths containing ! remain intact.
if not defined JAT_PYTHON goto :discover
call :validate
exit /b %errorlevel%
:discover
set "JAT_PYTHON="
if exist "%~dp0..\runtime\python38.path" set /p "JAT_PYTHON=" < "%~dp0..\runtime\python38.path"
if defined JAT_PYTHON call :validate
if defined JAT_PYTHON exit /b 0
for /f "delims=" %%P in ('py -3.8 -c "import sys; print(sys.executable)" 2^>nul') do (
  set "JAT_PYTHON=%%P"
  call :validate
)
if defined JAT_PYTHON exit /b 0
for %%P in ("%LocalAppData%\Programs\Python\Python38\python.exe" "%ProgramFiles%\Python38\python.exe" "C:\Python38\python.exe") do (
  if not defined JAT_PYTHON (
    set "JAT_PYTHON=%%~P"
    call :validate
  )
)
if defined JAT_PYTHON exit /b 0
for /f "delims=" %%P in ('where python 2^>nul') do (
  if not defined JAT_PYTHON (
    set "JAT_PYTHON=%%P"
    call :validate
  )
)
if defined JAT_PYTHON exit /b 0
echo Khong tim thay Python 3.8.10 x64. Mo INSTALL_WIN7.bat de chon python.exe.
exit /b 20
:validate
if not exist "%JAT_PYTHON%" goto :invalid
"%JAT_PYTHON%" -I -c "import sys,struct; sys.exit(0 if sys.version_info[:3] == (3,8,10) and struct.calcsize('P') == 8 else 20)" >nul 2>&1
if errorlevel 1 goto :invalid
exit /b 0
:invalid
set "JAT_PYTHON="
exit /b 20
