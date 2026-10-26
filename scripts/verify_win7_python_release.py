"""Windows artifact smoke test; no keys, network calls, old EXE or user runtime."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if os.name != 'nt' or sys.version_info[:3] != (3, 8, 10):
        raise SystemExit('Requires native Windows CPython 3.8.10')
    archive = ROOT/'dist'/'JAT-Design-Win7-Python38-StartupFix-20261026.zip'
    with tempfile.TemporaryDirectory(prefix='JAT source & ! ') as folder:
        base = Path(folder)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
            z.extractall(base)
        source = base/'JAT-Design-Win7-Python38'
        check = subprocess.run([sys.executable, '-X', 'utf8', str(source/'run_win7_python.py'), '--check'], cwd=str(base), capture_output=True)
        if check.returncode:
            raise RuntimeError('Extracted-source offline check failed (code %s)' % check.returncode)
        env = os.environ.copy()
        env.update(JAT_PYTHON=sys.executable, JAT_NO_PAUSE='1', JAT_ASCII_CONSOLE='1')
        bat = source/'START_WIN7_PYTHON.bat'
        # cmd /s /c requires a wrapping quote pair in addition to the quoted path.
        result = subprocess.run('"%s" /d /s /c ""%s""' % (env.get('COMSPEC', 'cmd.exe'), bat),
                                cwd=str(base), env=env, input=b'', capture_output=True)
        if result.returncode != 2:
            raise RuntimeError('Extracted BAT failed to preserve safe noninteractive exit: %s' % result.returncode)
        # Real launchers from the extracted directory, not imports from a developer checkout.
        def batch(name, code, marker):
            script = source/name
            result = subprocess.run('"%s" /d /s /c ""%s""' % (env.get('COMSPEC', 'cmd.exe'), script),
                                    cwd=str(base), env=env, input=b'', capture_output=True)
            if result.returncode != code or marker not in result.stdout:
                raise RuntimeError('Extracted batch check failed: '+name+' code='+str(result.returncode))
        batch('CHECK_WIN7.bat', 33, b'PROFILE_DB_MISSING')
        batch('SELF_TEST_WIN7.bat', 0, b'PASS SELFTEST')
        for name in ('SETUP_API.bat', 'INIT_PROFILE_WIN7.bat', 'EXPORT_PROFILE_WIN7.bat'):
            batch(name, 2, b'Can CMD tuong tac')
        if (source/'runtime').exists():
            raise RuntimeError('Offline/start guard created user runtime unexpectedly')
        # A real batch must retain the interpreter's preflight failure code.
        entry = source/'run_win7_python.py'; original = entry.read_bytes()
        try:
            entry.write_text('import sys;sys.exit(21)', encoding='ascii')
            batch('INSTALL_WIN7.bat', 21, b'Ket qua: 21')
        finally: entry.write_bytes(original)
    print('PASS: extracted ZIP Python/SQLite/DPAPI and actual START BAT (spaces, & and ! in path); no API or messages')


if __name__ == '__main__':
    main()
