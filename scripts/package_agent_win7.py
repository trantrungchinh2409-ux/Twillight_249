"""Agent add-on allowlist. Never overwrite accepted bot files or include runtime."""
from pathlib import Path
import hashlib
import json
import zipfile
ROOT=Path(__file__).resolve().parents[1]
NAME='JAT-Design-Agent-Win7-Followup-Diagnosis-20261027.zip'
FILES=('FOLLOWUP_DIAGNOSIS_VI.md','PROBE_FOLLOWUP_WIN7.bat','jat_design/agent_followup_probe.py','tests/test_agent_followup_diagnosis.py','AGENT_NATIVE_TEST_REPORT.json','run_agent_win7.py','START_AGENT_WIN7.bat','SETUP_AGENT_NAMES_WIN7.bat','CHECK_AGENT_WIN7.bat',
       'SELF_TEST_AGENT_WIN7.bat','ROLLBACK_WIN7.bat','AGENT_BASELINE.json','README_AGENT_WIN7_VI.md',
       'VALIDATION_AGENT_WIN7.md','AGENT_VERIFICATION.json','scripts/package_agent_win7.py','tests/test_agent_win7.py',
       'jat_design/agent_app.py','jat_design/agent_store.py','jat_design/agent_engine.py',
       'jat_design/agent_names.py','jat_design/agent_gemini.py','jat_design/agent_transport.py')


def package(output=None):
    baseline=json.loads((ROOT/'AGENT_BASELINE.json').read_text())
    for name,digest in baseline['sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Accepted base changed')
    if set(FILES)&set(baseline['sha256']):raise ValueError('Add-on cannot replace accepted source')
    output=Path(output) if output else ROOT/'downloads'/NAME
    output.parent.mkdir(exist_ok=True,parents=True);manifest={}
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name in FILES:
            p=ROOT/name
            if p.is_symlink() or not p.is_file():raise ValueError('Invalid input')
            data=p.read_bytes();manifest[name]=hashlib.sha256(data).hexdigest()
            info=zipfile.ZipInfo('JAT-Agent-Addon/'+name,(2026,10,27,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
        z.writestr('JAT-Agent-Addon/AGENT_MANIFEST.json',json.dumps({'base':baseline['base_commit'],'sha256':manifest},indent=2))
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        for name,digest in manifest.items():assert hashlib.sha256(z.read('JAT-Agent-Addon/'+name)).hexdigest()==digest
    digest=hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(digest+'  '+output.name+'\n',encoding='ascii')
    print(output.name,'files='+str(len(manifest)+1),'sha256='+digest)
    return output


if __name__=='__main__':package()
