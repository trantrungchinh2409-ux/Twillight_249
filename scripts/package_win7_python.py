"""Reproducible source-only archive; never glob runtime, credentials or native DLLs."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'JAT-Design-Win7-Python38.zip'


def inputs(root=ROOT):
    names = ['INSTALL_WIN7.bat', 'START_WIN7_PYTHON.bat', 'run_win7_python.py',
             'run_portable.py', 'check_zalo_tls.py', 'zalo_cert_check.py', 'inspect_zalo_windows_chain.ps1', 'SYSTEM_PROMPT.txt', 'requirements.txt',
             'README_WIN7_PYTHON_VI.md', 'VALIDATION_WIN7_PYTHON.md',
             'scripts/find_python38.bat', 'scripts/package_win7_python.py', 'scripts/verify_win7_python_release.py']
    files = [root/name for name in names]
    files += list((root/'jat_design').glob('*.py'))
    files += list((root/'tests').glob('*.py'))
    for path in files:
        if path.is_symlink() or not path.is_file() or path.resolve().parent == root/'runtime':
            raise ValueError('Unsafe or missing release input: '+path.name)
    return sorted(set(files))


def package(output=None):
    output = Path(output) if output else ROOT/'dist'/NAME
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {}
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in inputs():
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            manifest[name] = hashlib.sha256(data).hexdigest()
            info = zipfile.ZipInfo('JAT-Design-Win7-Python38/'+name, (2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
        info = zipfile.ZipInfo('JAT-Design-Win7-Python38/SOURCE_MANIFEST.json', (2026, 10, 26, 0, 0, 0))
        archive.writestr(info, json.dumps({'base_commit': '61a1a3d9884938736ee83a762e3cdf10cc570105',
            'runtime': 'installed CPython 3.8.10 x64; standard library only', 'sha256': manifest}, indent=2).encode('utf-8'))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError('Archive CRC failed')
        for name, digest in manifest.items():
            if hashlib.sha256(archive.read('JAT-Design-Win7-Python38/'+name)).hexdigest() != digest:
                raise ValueError('Archive readback mismatch')
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n', encoding='ascii')
    print(output.name, 'files='+str(len(manifest)+1), 'sha256='+digest)
    return output


if __name__ == '__main__':
    package()
