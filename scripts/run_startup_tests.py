"""Record real offline suite totals, never API credentials or user state."""
import io
import json
from pathlib import Path
import platform
import sys
import unittest

root = Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
suite = unittest.defaultTestLoader.discover(str(root/'tests'))
buffer = io.StringIO()
result = unittest.TextTestRunner(stream=buffer, verbosity=1).run(suite)
report = {'tests':result.testsRun,'passed':result.testsRun-len(result.skipped)-len(result.failures)-len(result.errors),
          'failures':len(result.failures),'errors':len(result.errors),
          'skipped':[{'test':str(test),'reason':reason} for test,reason in result.skipped],
          'runner':platform.platform(),'python':platform.python_version(),'live_zalo':'not run','live_gemini':'not run'}
(root/'dist').mkdir(exist_ok=True)
(root/'dist'/('tests-'+platform.python_version()+'.log')).write_text(buffer.getvalue(),encoding='utf-8')
(root/'dist'/('tests-'+platform.python_version()+'.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
raise SystemExit(0 if result.wasSuccessful() else 1)
