"""Certificate diagnostics only. Approved CA files are never packaged."""
from pathlib import Path
import hashlib
import json
import zipfile
ROOT = Path(__file__).resolve().parents[1]
FILES = ('CHECK_ZALO_CERT_WIN7.bat', 'zalo_cert_check.py', 'check_zalo_tls.py',
         'inspect_zalo_windows_chain.ps1', 'README_ZALO_CERT_CHECK_VI.md', 'scripts/find_python38.bat')


def package():
    out = ROOT/'downloads'/'JAT-Zalo-Certificate-Check-Win7.zip'
    out.parent.mkdir(exist_ok=True)
    manifest = {}
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            path = ROOT/name
            if path.is_symlink() or not path.is_file():
                raise ValueError('Unsafe input')
            data = path.read_bytes(); manifest[name] = hashlib.sha256(data).hexdigest()
            info = zipfile.ZipInfo('JAT-Zalo-Certificate-Check-Win7/'+name, (2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED; z.writestr(info, data)
        z.writestr('JAT-Zalo-Certificate-Check-Win7/MANIFEST.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for name, digest in manifest.items():
            assert hashlib.sha256(z.read('JAT-Zalo-Certificate-Check-Win7/'+name)).hexdigest() == digest
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix('.zip.sha256').write_text(digest+'  '+out.name+'\n', encoding='ascii')
    print(out.name, 'files='+str(len(manifest)+1), 'sha256='+digest)


if __name__ == '__main__':
    package()
