"""Reproducible onedir candidate. Build/test target Win7 separately before approval."""
from pathlib import Path
import platform
import os
import shutil
import struct
import subprocess
import sys
import PyInstaller

ROOT = Path(__file__).resolve().parents[1]
if sys.platform != 'win32' or sys.version_info[:3] != (3, 8, 10) or struct.calcsize('P') != 8:
    raise SystemExit('Build needs official CPython 3.8.10 x64 on Windows, not Python 3.9+.')
if PyInstaller.__version__ != '5.13.2': raise SystemExit('Pinned PyInstaller 5.13.2 required.')
subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'], cwd=ROOT, check=True)
# Do not let unrelated user PATH inject CRT/OpenSSL DLLs into the package.
env = os.environ.copy()
env['PATH'] = os.pathsep.join([str(Path(sys.executable).parent), str(Path(env['SYSTEMROOT'])/'System32'), env['SYSTEMROOT']])
spec_dir = ROOT/'build/win7-candidate'; spec_dir.mkdir(parents=True, exist_ok=True)
spec = spec_dir/'JATDesign.spec'
spec.write_text("""from pathlib import Path
import sys
root = Path(SPECPATH).resolve().parents[1]
a = Analysis([str(root/'run_portable.py')], pathex=[str(root)], binaries=[], datas=[],
             hiddenimports=[], hookspath=[], runtime_hooks=[], excludes=[], noarchive=False)
# Never redistribute UCRT/API-set DLLs scavenged from a newer OS or another app.
# Target Windows 7 must have an official compatible UCRT supplied by its administrator.
a.binaries = [x for x in a.binaries if not (Path(x[0]).name.lower().startswith('api-ms-')
              or Path(x[0]).name.lower() == 'ucrtbase.dll')]
for name, source, kind in a.binaries:
    if Path(name).suffix.lower() in ('.dll', '.pyd'):
        if Path(source).resolve().parent != Path(sys.base_prefix).resolve():
            raise RuntimeError('Unapproved native dependency source: '+Path(source).name)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='JATDesign', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=True)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=False, name='JATDesign')
""", encoding='utf-8')
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                '--distpath', 'dist/win7-candidate', '--workpath', 'build/win7-candidate', str(spec)],
               cwd=ROOT, env=env, check=True)
folder = ROOT/'dist/win7-candidate/JATDesign'
for file in (ROOT/'portable').glob('*.bat'): shutil.copy2(file, folder/file.name)
for name in ('SYSTEM_PROMPT.txt', 'README_WIN7_VI.md', 'THIRD_PARTY_WIN7.md'):
    shutil.copy2(ROOT/name, folder/name)
license_file = Path(sys.base_prefix)/'LICENSE.txt'
if not license_file.exists(): raise SystemExit('PSF LICENSE.txt missing from official Python distribution.')
shutil.copy2(license_file, folder/'LICENSE-python.txt')
pyi_license = Path(PyInstaller.__file__).resolve().parent.parent/'pyinstaller-5.13.2.dist-info/COPYING.txt'
if not pyi_license.exists(): raise SystemExit('PyInstaller bootloader exception license missing.')
shutil.copy2(pyi_license, folder/'LICENSE-PyInstaller.txt')
subprocess.run([str(folder/'JATDesign.exe'), '--self-test'], check=True)
print('Built candidate on %s. Windows 7 actual test still required.' % platform.platform())

