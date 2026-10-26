@echo off
setlocal DisableDelayedExpansion
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul
cd /d "%~dp0"
call "%~dp0scripts\find_python38.bat"
if not errorlevel 1 goto :ready
echo Nhap duong dan day du python.exe 3.8.10 x64, khong kem dau ngoac kep.
set "JAT_PYTHON="
set /p "JAT_PYTHON=Python: "
if not defined JAT_PYTHON goto :failed
call "%~dp0scripts\find_python38.bat"
if errorlevel 1 goto :failed
:ready
"%JAT_PYTHON%" -X utf8 -B "%~dp0run_win7_python.py" --check
if errorlevel 1 goto :failed
"%JAT_PYTHON%" -X utf8 -B -c "import sys; from pathlib import Path; p=Path(sys.argv[1]); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(sys.executable,encoding='utf-8')" "%~dp0runtime\python38.path"
if errorlevel 1 goto :failed
"%JAT_PYTHON%" -X utf8 -B "%~dp0run_win7_python.py" --install
set "JAT_EXIT=%errorlevel%"
goto :done
:failed
set "JAT_EXIT=1"
echo Chua san sang. Giu runtime cu, khong tai DLL la va khong xoa DB.
:done
echo.
echo Ket qua: %JAT_EXIT%
if not defined JAT_NO_PAUSE pause
endlocal & exit /b %JAT_EXIT%
