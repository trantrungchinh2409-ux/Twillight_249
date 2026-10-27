"""Single native validation run; blocks sockets and publishes only finite test metadata."""
import contextlib
import io
import json
from pathlib import Path
import platform
import socket
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
out=ROOT/'AGENT_NATIVE_TEST_REPORT.json'
report={'python':platform.python_version(),'platform':platform.platform(),'network_blocked':True,
        'live_zalo':'not run','live_gemini':'not run','typing_live_verified':False,'win7_live_verified':False}
if sys.platform!='win32' or sys.version_info[:3]!=(3,8,10):
    report.update(status='FAIL',reason='Windows CPython3.8.10 required')
    out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    raise SystemExit(1)
buffer=io.StringIO()
with contextlib.redirect_stdout(buffer),contextlib.redirect_stderr(buffer),\
     patch.object(socket,'create_connection',side_effect=AssertionError('Network disabled in offline validation')),\
     patch.object(socket.socket,'connect',side_effect=AssertionError('Network disabled in offline validation')):
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    result=unittest.TextTestRunner(stream=buffer,verbosity=1).run(suite)
report.update(status='PASS' if result.wasSuccessful() else 'FAIL',tests=result.testsRun,
              passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
              failures=[test.id() for test,_ in result.failures],errors=[test.id() for test,_ in result.errors],
              skipped=[{'test':test.id(),'reason':reason} for test,reason in result.skipped])
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
raise SystemExit(0 if result.wasSuccessful() else 1)
