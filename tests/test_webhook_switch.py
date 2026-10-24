"""Synthetic API data only; never proof of a real webhook change."""
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from jat_design import webhook_switch as w
from jat_design.official_api import APIError, ProtocolError, Transport
from test_official_api import Opener
from test_polling_test import Fake

INFO = {'url': 'https://synthetic-worker.example/webhook', 'updated_at': 123}
SECRET = 'synthetic-secret-not-real'


class SwitchTests(unittest.TestCase):
    def test_native_dpapi_roundtrip(self):
        plaintext = b'synthetic secret only'
        ciphertext = w.protect(plaintext)
        self.assertNotIn(plaintext, ciphertext)
        self.assertEqual(w.protect(ciphertext, decrypt=True), plaintext)

    def test_backup_written_before_delete_then_verify(self):
        with tempfile.TemporaryDirectory() as folder:
            class Checked(Fake):
                def post(self, method, payload, timeout):
                    if method == 'deleteWebhook':
                        files = list(Path(folder).glob('*.bin'))
                        self_test.assertEqual(len(files), 1)
                        backup = json.loads(w.protect(files[0].read_bytes(), decrypt=True))
                        self_test.assertEqual(backup['secret_token'], SECRET)
                    return super().post(method, payload, timeout)
            self_test = self
            api = Checked(INFO, INFO, {'url': ''}, {'url': ''})
            path = w.disable(api, 'dummy-bot', SECRET, Path(folder))
            self.assertEqual([x[0] for x in api.calls],
                             ['getWebhookInfo', 'getWebhookInfo', 'deleteWebhook', 'getWebhookInfo'])
            self.assertEqual(json.loads(path.with_suffix('.status.json').read_text())['phase'],
                             'disabled_confirmed')
            self.assertNotIn(SECRET.encode(), path.read_bytes())

    def test_backup_failure_never_deletes(self):
        api = Fake(INFO)
        with tempfile.TemporaryDirectory() as folder, patch.object(w, 'protect', side_effect=OSError):
            with self.assertRaises(OSError):
                w.disable(api, 'dummy-bot', SECRET, Path(folder))
        self.assertEqual([x[0] for x in api.calls], ['getWebhookInfo'])

    def test_concurrent_change_never_deletes(self):
        api = Fake(INFO, {'url': 'https://other.example/webhook'})
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ProtocolError):
                w.disable(api, 'dummy-bot', SECRET, Path(folder))
        self.assertNotIn('deleteWebhook', [x[0] for x in api.calls])

    def test_delete_timeout_not_retried_and_backup_remains(self):
        api = Fake(INFO, INFO, APIError('private details'))
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(APIError):
                w.disable(api, 'dummy-bot', SECRET, Path(folder))
            self.assertEqual(len(list(Path(folder).glob('*.bin'))), 1)
        self.assertEqual([x[0] for x in api.calls].count('deleteWebhook'), 1)

    def test_restore_same_bot_url_and_secret(self):
        with tempfile.TemporaryDirectory() as folder:
            backup = w.disable(Fake(INFO, INFO, True, {'url': ''}), 'dummy-bot', SECRET, Path(folder))
            api = Fake({'url': ''}, {'verification': {'ok': False}}, INFO)
            self.assertEqual(w.restore(api, 'dummy-bot', backup), 'restored_url_callback_unverified')
            self.assertEqual(api.calls[1][1], {'url': INFO['url'], 'secret_token': SECRET})
            wrong = Fake()
            with self.assertRaises(ValueError):
                w.restore(wrong, 'wrong-bot', backup)
            self.assertEqual(wrong.calls, [])

    def test_missing_secret_no_mutation(self):
        with tempfile.TemporaryDirectory() as folder:
            api = Fake(INFO)
            with self.assertRaises(ValueError):
                w.disable(api, 'dummy-bot', '', Path(folder))
            self.assertEqual(len(api.calls), 1)

    def test_transport_accepts_documented_delete_boolean(self):
        api = Transport('synthetic-token', Opener({'ok': True, 'result': True}))
        self.assertIs(api.post('deleteWebhook', {}, 15), True)
