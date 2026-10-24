import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from jat_design.key_vault import Vault, KeyPool, key_specific
from jat_design.gemini_client import GeminiError, error_details
from jat_design.setup_api import add_flow, check_one, show


class VaultTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'keys.dpapi'
        self.vault = Vault(self.path)
    def tearDown(self): self.temp.cleanup()

    def test_native_dpapi_many_keys_duplicate_delete_primary_restart(self):
        for i in range(12): self.assertTrue(self.vault.add('synthetic-private-key-'+str(i)))
        self.assertFalse(self.vault.add('synthetic-private-key-0'))
        self.vault.primary(8)
        self.vault.remove(1)
        reopened = Vault(self.path)
        self.assertEqual(len(reopened.data['items']), 11)
        self.assertEqual(reopened.ordered()[0]['key'], 'synthetic-private-key-8')
        self.assertNotIn(b'synthetic-private-key', self.path.read_bytes())
        # Fresh Python process, same Windows user. Do not output secret values.
        result = subprocess.run([sys.executable, '-c',
            'import sys;from jat_design.key_vault import Vault;print(len(Vault(sys.argv[1]).data["items"]))',
            str(self.path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), '11')

    def test_menu_flow_enter_more_y_finish_hidden_input_callback(self):
        keys, commands, outputs = iter(['dummy-key-one', 'dummy-key-two', 'dummy-key-one']), iter(['', '', 'Y']), []
        add_flow(self.vault, read_secret=lambda _: next(keys), read_command=lambda _: next(commands), output=outputs.append)
        self.assertEqual(len(Vault(self.path).data['items']), 2)
        self.assertNotIn('dummy-key', str(outputs))

    def test_failure_does_not_replace_existing_encrypted_store(self):
        self.vault.add('synthetic-original-key')
        before = self.path.read_bytes()
        with patch('jat_design.key_vault.protect', side_effect=OSError('private-error')):
            with self.assertRaises(OSError): self.vault.add('synthetic-other-key')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(len(Vault(self.path).data['items']), 1)
        self.assertFalse(list(self.path.parent.glob('*.tmp')))

    def test_delete_last_key_is_persisted(self):
        self.vault.add('dummy-one'); self.vault.remove(0)
        reopened = Vault(self.path)
        self.assertEqual(reopened.data['items'], [])
        self.assertIsNone(reopened.data['primary'])

    def factory(self, behavior, calls):
        class Fake:
            def __init__(self, key, prompt): self.key, self.model = key, None
            def select_model(self): self.model = 'models/gemini-3.5-flash-lite'; return self.model
            def generate(self, question):
                calls.append(self.key)
                value = behavior[self.key]
                if isinstance(value, Exception): raise value
                return value
        return Fake

    def populate(self):
        self.vault.add('dummy-primary'); self.vault.add('dummy-backup')

    def test_primary_invalid_falls_back_and_remains_invalid_after_reload(self):
        self.populate(); calls = []
        factory = self.factory({'dummy-primary': GeminiError('private', 400, 'http', reason='API_KEY_INVALID'),
                                'dummy-backup': 'Đáp án.'}, calls)
        pool = KeyPool(self.vault, 'prompt', factory, output=lambda _: None)
        self.assertEqual(pool.generate('question'), 'Đáp án.')
        self.assertEqual(calls, ['dummy-primary', 'dummy-backup'])
        pool = KeyPool(Vault(self.path), 'prompt', factory, output=lambda _: None)
        self.assertEqual(pool.generate('new question'), 'Đáp án.')
        self.assertEqual(calls[-1], 'dummy-backup')
        self.assertEqual(calls.count('dummy-primary'), 1)

    def test_429_waits_persistently_and_never_rotates(self):
        self.populate(); calls = []
        factory = self.factory({'dummy-primary': GeminiError('private', 429, 'http', retry_after=120),
                                'dummy-backup': 'Do not use'}, calls)
        pool = KeyPool(self.vault, 'prompt', factory)
        with self.assertRaises(GeminiError): pool.generate('question')
        reopened = Vault(self.path)
        self.assertGreater(reopened.wait_remaining(), 115)
        pool = KeyPool(reopened, 'prompt', factory)
        with self.assertRaises(GeminiError): pool.generate('next question')
        self.assertEqual(calls, ['dummy-primary'])

    def test_billing_network_permission_and_model_do_not_rotate(self):
        self.populate()
        for error in (GeminiError('private', 402, 'http'), GeminiError('private', kind='network'),
                      GeminiError('private', 403, 'http'), GeminiError('private', 404, 'http')):
            calls = []
            pool = KeyPool(self.vault, 'prompt', self.factory({'dummy-primary': error, 'dummy-backup': 'no'}, calls))
            with self.assertRaises(GeminiError): pool.generate('question')
            self.assertEqual(calls, ['dummy-primary'])

    def test_check_is_one_selected_key_not_all(self):
        self.populate(); calls = []
        status = check_one(self.vault, 1, 'prompt', self.factory({'dummy-backup': 'ok'}, calls))
        self.assertEqual(status, 'generation_verified')
        self.assertEqual(calls, ['dummy-backup'])
        output = []
        show(self.vault, output.append)
        self.assertNotIn('dummy-', str(output))

    def test_retry_after_and_retry_info_use_longest_without_body_text(self):
        body = {'error': {'status': 'RESOURCE_EXHAUSTED', 'message': 'secret text',
            'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '72.5s'}]}}
        self.assertEqual(error_details(body, {'Retry-After': '120'}), ('RESOURCE_EXHAUSTED', None, 120))
        result = error_details(body, {'Retry-After': 'Thu, 01 Jan 1970 00:03:20 GMT'}, now=lambda: 100)
        self.assertEqual(result[2], 100)
        self.assertNotIn('secret', str(result))

    def test_key_reason_does_not_override_quota_or_billing(self):
        self.assertFalse(key_specific(GeminiError('private', 429, 'http', reason='API_KEY_INVALID')))
        self.assertFalse(key_specific(GeminiError('private', 403, 'http', reason='BILLING_DISABLED')))
