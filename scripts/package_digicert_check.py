"""Package standalone downloader/diagnostic only: no CA prebundled, no bot/runtime."""
from pathlib import Path
import hashlib
import json
import zipfile
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
FILES=('CHECK_ZALO_DIGICERT_WIN7.bat','check_zalo_digicert.py','digicert_bundle.py',
       'check_zalo_tls.py','README_ZALO_DIGICERT_VI.md','scripts/find_python38.bat',
       'scripts/fetch_digicert_bundle.py')


def package():
    out=ROOT/'downloads'/'JAT-Zalo-DigiCert-Win7.zip';out.parent.mkdir(exist_ok=True)
    hashes={}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            p=ROOT/name
            if p.is_symlink() or not p.is_file():raise ValueError('Unsafe input')
            data=p.read_bytes();hashes[name]=hashlib.sha256(data).hexdigest()
            info=zipfile.ZipInfo('JAT-Zalo-DigiCert-Win7/'+name,(2026,10,26,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
        z.writestr('JAT-Zalo-DigiCert-Win7/MANIFEST.json',json.dumps(hashes,indent=2))
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        for name,digest in hashes.items():assert hashlib.sha256(z.read('JAT-Zalo-DigiCert-Win7/'+name)).hexdigest()==digest
    digest=hashlib.sha256(out.read_bytes()).hexdigest()
    out.with_suffix('.zip.sha256').write_text(digest+'  '+out.name+'\n',encoding='ascii')
    print(out.name,'files='+str(len(hashes)+1),'sha256='+digest)


if __name__=='__main__':package()
