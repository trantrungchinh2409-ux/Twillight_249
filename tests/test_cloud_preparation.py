import contextlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from jat_design.cloud_worker import run, settings


class CloudPreparationTests(unittest.TestCase):
    def test_default_off_never_opens_zalo_or_gemini(self):
        stop = threading.Event(); stop.set()
        with patch('jat_design.cloud_worker.Transport') as zalo, patch('jat_design.cloud_worker.Gemini') as gemini:
            self.assertEqual(run({}, stop), 0)
            zalo.assert_not_called(); gemini.assert_not_called()

    def test_cannot_enable_without_local_cutover_confirmation(self):
        with self.assertRaises(ValueError): settings({'BOT_ENABLED': 'true'})

    def test_volume_required_before_any_network(self):
        env = {'BOT_ENABLED': 'true', 'LOCAL_POLLERS_STOPPED': 'true',
               'ZALO_BOT_TOKEN': 'dummy', 'GEMINI_API_KEY': 'dummy',
               'ZALO_GROUP_ID': 'dummy', 'EXPECTED_BOT_ID_SHA256': 'a'*64}
        with self.assertRaises(ValueError): settings(env)

    def test_persistent_hold_prevents_api_calls_on_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'cloud_hold.json').write_text('{}')
            env = {'BOT_ENABLED': 'true', 'LOCAL_POLLERS_STOPPED': 'true',
                   'ZALO_BOT_TOKEN': 'dummy', 'GEMINI_API_KEY': 'dummy',
                   'ZALO_GROUP_ID': 'dummy', 'EXPECTED_BOT_ID_SHA256': 'a'*64,
                   'DATA_DIR': str(root), 'RAILWAY_VOLUME_MOUNT_PATH': str(root)}
            stop = threading.Event(); stop.set()
            with patch('jat_design.cloud_worker.PollingLease', return_value=contextlib.nullcontext()), \
                 patch('jat_design.cloud_worker.Transport') as api:
                self.assertEqual(run(env, stop), 0)
                api.assert_not_called()
