@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -c "import sys,ssl,sqlite3,ctypes; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if not errorlevel 1 (
    py -3 -m jat_design.polling_test
    goto done
  )
)
where python >nul 2>nul
if not errorlevel 1 (
  python -c "import sys,ssl,sqlite3,ctypes; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
  if not errorlevel 1 (
    python -m jat_design.polling_test
    goto done
  )
)
echo Can Python 3.10 tro len. Bao Codex de cai dat.
:done
echo.
echo Nhan phim bat ky de dong cua so.
pause >nul
endlocal
