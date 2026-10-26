import io
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from jat_design import win7_python as launcher


class SourceLauncherTests(unittest.TestCase):
    def test_reject_wrong_python_bitness_or_old_service_pack(self):
        for args in [((3, 12, 0), 64, True, (10, 0, 0)),
                     ((3, 8, 10), 32, True, (6, 1, 1)),
                     ((3, 8, 10), 64, False, None),
                     ((3, 8, 10), 64, True, (6, 1, 0))]:
            self.assertIsNotNone(launcher.compatible(*args))
        self.assertIsNone(launcher.compatible((3, 8, 10), 64, True, (6, 1, 1)))
        self.assertIsNone(launcher.compatible((3, 8, 10), 64, True, (10, 0, 0)))

    def test_failed_preflight_cannot_start_setup_or_network(self):
        with patch.object(launcher, 'check', return_value=21), patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            self.assertEqual(launcher.main(['--setup']), 21)

    def test_redirected_input_never_starts_bot(self):
        with patch.object(launcher, 'check', return_value=0), patch('sys.stdin', io.StringIO('sensitive\n')), patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            self.assertEqual(launcher.main([]), 2)

    def test_import_profile_uses_python_input_not_shell_and_keeps_target_defaults(self):
        from jat_design import portable_profile
        with patch('builtins.input', return_value='"C:\\private folder\\profile.zip"'), patch.object(portable_profile, 'main', return_value=0) as main:
            self.assertEqual(launcher.profile('--import-profile'), 0)
            self.assertEqual(main.call_args[0][0], ['--import', 'C:\\private folder\\profile.zip'])
        with patch('builtins.input', return_value=''), patch.object(portable_profile, 'main') as main:
            self.assertEqual(launcher.profile('--import-profile'), 0)
            main.assert_not_called()

    def test_check_does_not_change_existing_runtime(self):
        runtime = launcher.BASE/'runtime'
        before = sorted(str(p) for p in runtime.rglob('*')) if runtime.exists() else []
        with patch.object(launcher, 'check', return_value=0):
            self.assertEqual(launcher.main(['--check']), 0)
        self.assertEqual(before, sorted(str(p) for p in runtime.rglob('*')) if runtime.exists() else [])

    @unittest.skipUnless(os.name == 'nt' and sys.version_info[:3] == (3, 8, 10) and struct.calcsize('P') == 8, 'Native Windows Python 3.8.10 x64 required')
    def test_native_offline_check_and_batch_selection_exit_status(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            self.assertEqual(launcher.check(), 0)
        root = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env['JAT_PYTHON'] = sys.executable
        helper = str(root/'scripts'/'find_python38.bat')
        with tempfile.TemporaryDirectory() as cwd:
            good = subprocess.run([env.get('COMSPEC', 'cmd.exe'), '/d', '/c', helper], cwd=cwd, env=env, capture_output=True)
            self.assertEqual(good.returncode, 0, good.stdout.decode(errors='replace'))
            env['JAT_PYTHON'] = str(root/'missing-python.exe')
            bad = subprocess.run([env.get('COMSPEC', 'cmd.exe'), '/d', '/c', helper], cwd=cwd, env=env, capture_output=True)
            self.assertEqual(bad.returncode, 20)


if __name__ == '__main__':
    unittest.main()
