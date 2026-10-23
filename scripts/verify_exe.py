"""Validate PE x64 structure, then execute the actual EXE's offline self-test."""
import hashlib
import json
import platform
from pathlib import Path
import struct
import subprocess
import sys

path = Path(sys.argv[1]).resolve()
data = path.read_bytes()
if len(data) < 64 or data[:2] != b'MZ':
    raise SystemExit('Not a PE executable')
offset = struct.unpack_from('<I', data, 60)[0]
if data[offset:offset + 4] != b'PE\x00\x00':
    raise SystemExit('Invalid PE signature')
if struct.unpack_from('<H', data, offset + 4)[0] != 0x8664:
    raise SystemExit('Not PE x64')
if struct.unpack_from('<H', data, offset + 24)[0] != 0x20b:
    raise SystemExit('Not PE32+')
if sys.platform != 'win32':
    raise SystemExit('Must execute PE self-test on Windows')
result = subprocess.run([str(path), '--self-test'], capture_output=True,
                        timeout=60, text=True)
print(result.stdout)
if result.returncode or 'PASS: internal mock only' not in result.stdout:
    raise SystemExit('EXE self-test failed')
blocked = subprocess.run([str(path), '--live'], capture_output=True,
                         timeout=60, text=True)
if blocked.returncode != 2 or 'LIVE BLOCKED' not in blocked.stderr:
    raise SystemExit('EXE live safety gate failed')
report = {'file': path.name, 'sha256': hashlib.sha256(data).hexdigest(),
          'bytes': len(data), 'format': 'PE32+ x64',
          'runner_os': platform.platform(), 'python': platform.python_version(),
          'exe_mock_self_test': 'passed', 'live_gate': 'blocked as expected',
          'zalo_live_test': 'not run', 'windows_7_test': 'not run'}
path.with_suffix('.verification.json').write_text(
    json.dumps(report, indent=2) + '\n', encoding='utf-8')
