"""Small independent diagnostic archive: no bot modules or runtime."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
FILES = ('CHECK_ZALO_TLS_WIN7.bat', 'check_zalo_tls.py', 'README_ZALO_TLS_CHECK_VI.md', 'scripts/find_python38.bat')


def package():
    output = ROOT/'downloads'/'JAT-Zalo-TLS-Check-Win7.zip'
    output.parent.mkdir(exist_ok=True)
    manifest = {}
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            path = ROOT/name
            if path.is_symlink() or not path.is_file():
                raise ValueError('Unsafe input')
            data = path.read_bytes()
            manifest[name] = hashlib.sha256(data).hexdigest()
            info = zipfile.ZipInfo('JAT-Zalo-TLS-Check-Win7/'+name, (2026, 10, 26, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
        archive.writestr('JAT-Zalo-TLS-Check-Win7/MANIFEST.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for name, digest in manifest.items():
            assert hashlib.sha256(archive.read('JAT-Zalo-TLS-Check-Win7/'+name)).hexdigest() == digest
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n', encoding='ascii')
    print(output.name, 'files='+str(len(manifest)+1), 'sha256='+digest)


if __name__ == '__main__':
    package()
