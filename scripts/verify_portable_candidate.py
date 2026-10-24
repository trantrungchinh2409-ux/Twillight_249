"""Run actual onedir EXE, inspect native provenance, exercise private transfer."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import pefile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jat_design.auto_reply import GROUP_SAMPLE, TRIGGER, hashed, verified_group
from jat_design.managed_limits import ManagedResponder
from jat_design.portable_profile import APPROVAL
from jat_design.state import State
from jat_design.webhook_switch import protect

folder = ROOT/'dist/win7-candidate/JATDesign'
exe = folder/'JATDesign.exe'
report = {'runner_os': platform.platform(), 'windows_7_verified': False, 'zalo_live': 'not run',
          'lock_screen_win7': 'not run', 'network_loss_win7': 'not run', 'native_files': []}
for file in sorted(folder.iterdir()):
    if file.suffix.lower() not in ('.exe', '.dll', '.pyd'): continue
    pe = pefile.PE(str(file))
    assert pe.FILE_HEADER.Machine == 0x8664
    assert (pe.OPTIONAL_HEADER.MajorOperatingSystemVersion, pe.OPTIONAL_HEADER.MinorOperatingSystemVersion) <= (6, 1)
    if file != exe:
        source = Path(sys.base_prefix)/file.name
        assert source.exists() and source.read_bytes() == file.read_bytes(), 'Non-PSF native dependency'
    report['native_files'].append({'file': file.name, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
          'machine': 'x64', 'imports': [x.dll.decode() for x in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', [])]})
assert not list(folder.glob('api-ms-*.dll')) and not (folder/'ucrtbase.dll').exists()
report['ucrt'] = 'not bundled; official compatible UCRT required on target'
with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp); env = os.environ.copy()
    env['PATH'] = str(Path(env['SYSTEMROOT'])/'System32')  # No Python on PATH.
    def run(args, expected=0, binary=exe):
        result = subprocess.run([str(binary)]+args, cwd=temp, env=env, input='',
                                text=True, encoding='utf-8', capture_output=True, timeout=60)
        assert result.returncode == expected, 'Actual EXE verification failed: '+str(result.returncode)
        return result.stdout
    report['actual_exe_offline'] = json.loads(run(['--self-test']).strip())
    run(['--unsupported'], 2); run(['--setup'], 2); run([], 2)
    assert not (folder/'runtime').exists(), 'Verification must not create real runtime'
    source = temp/'synthetic-source'; source.mkdir()
    sample = {'event_name': 'message.text.received', 'message': {'text': TRIGGER+' private content removed',
              'chat': {'id': 'synthetic-group', 'chat_type': 'GROUP'}}}
    (source/GROUP_SAMPLE).write_bytes(protect(json.dumps(sample).encode()))
    state = State(source/'one_shot.db')
    try:
        state.reserve(hashed('synthetic-bot'), APPROVAL)
        state.mark(hashed('synthetic-bot'), APPROVAL, 'api_acknowledged:synthetic')
    finally: state.close()
    state = State(source/'ai_reply.db')
    try:
        engine = ManagedResponder(state, 'synthetic-bot', 'synthetic-group', clock=lambda: 1000)
        for _ in range(10): assert engine._claim_ai()
        state.reserve(engine.group_key, 'synthetic-dedup')
    finally: state.close()
    transfer = temp/'private-transfer.zip'
    run(['--export-profile', str(source), str(transfer)])
    destination = temp/'portable-target'; shutil.copytree(folder, destination)
    run(['--import-profile', str(transfer)], binary=destination/'JATDesign.exe')
    assert verified_group(destination/'runtime', 'synthetic-bot') == 'synthetic-group'
    state = State(destination/'runtime/ai_reply.db')
    try:
        engine = ManagedResponder(state, 'synthetic-bot', 'synthetic-group', clock=lambda: 1001)
        assert engine.status()['local_until'] == 1300
        assert not state.reserve(engine.group_key, 'synthetic-dedup')
    finally: state.close()
    run(['--import-profile', str(transfer)], 1, binary=destination/'JATDesign.exe')
    report['actual_exe_profile_transfer'] = 'passed; no overwrite, limits/dedup preserved, DPAPI reencrypted'
report['python_on_target_path'] = 'not required during EXE checks'
report['exe_sha256'] = hashlib.sha256(exe.read_bytes()).hexdigest()
(ROOT/'build/win7-candidate/portable-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('PASS: actual EXE, native provenance, offline safety, private transfer. Win7 NOT verified.')
