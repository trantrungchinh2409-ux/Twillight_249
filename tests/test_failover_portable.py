import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile
from unittest.mock import patch
from jat_design.auto_reply import GROUP_SAMPLE, TRIGGER, hashed, verified_group
from jat_design.gemini_client import GeminiError
from jat_design.key_vault import Vault, KeyPool
from jat_design.managed_ai import status_text
from jat_design.managed_limits import ManagedResponder
from jat_design.official_api import APIError
from jat_design.portable_profile import export_profile, import_profile, APPROVAL
from jat_design.reconnect import read_with_reconnect, retryable, wait
from jat_design.safe_audit import record
from jat_design.state import State
from jat_design.webhook_switch import protect


class FailoverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.folder = Path(self.temp.name)
        self.vault = Vault(self.folder/'vault.dpapi')
        for i in range(3): self.vault.add('synthetic-private-key-'+str(i))
        self.calls, self.messages = [], []
    def tearDown(self): self.temp.cleanup()
    def factory(self, outcomes):
        calls = self.calls
        class Fake:
            def __init__(self, key, prompt): self.key = key
            def generate(self, question):
                calls.append(self.key)
                result = outcomes[int(self.key.rsplit('-', 1)[1])]
                if isinstance(result, Exception): raise result
                return result
        return Fake
    def pool(self, outcomes, vault=None):
        return KeyPool(vault or self.vault, 'prompt', self.factory(outcomes), self.messages.append)

    def test_two_revoked_keys_switch_to_number_three_and_restart_keeps_active(self):
        outcomes = [GeminiError('hidden', 401, 'http'),
                    GeminiError('hidden', 403, 'http', reason='API_KEY_REVOKED'), 'answer']
        pool = self.pool(outcomes)
        self.assertEqual(pool.generate('question'), 'answer')
        self.assertEqual(len(self.calls), 3)
        self.assertIn('Đã chuyển sang API dự phòng #3', self.messages)
        self.assertNotIn('synthetic-private-key', str(self.messages)+str(pool.status()))
        reopened = self.pool(outcomes, Vault(self.vault.path))
        self.assertEqual(reopened.status()['active'], 3)
        reopened.generate('new question')
        self.assertEqual(len(self.calls), 4)
        self.assertEqual(self.calls[-1], 'synthetic-private-key-2')
        self.assertEqual(self.messages.count('Đã chuyển sang API dự phòng #3'), 1)

    def test_select_primary_resets_active_and_delete_active_reselects(self):
        self.vault.data['active'] = self.vault.data['items'][2]['id']; self.vault.save()
        self.vault.primary(1)
        self.assertEqual(self.pool(['a','b','c']).status()['active'], 2)
        self.vault.remove(1)
        pool = self.pool(['a','b','c'])
        self.assertEqual(pool.status()['active'], 1)

    def test_429_active_backup_stays_same_wait_persisted(self):
        pool = self.pool([GeminiError('safe', 401, 'http'), 'answer', 'unused'])
        pool.generate('first'); self.calls.clear()
        pool = self.pool(['unused', GeminiError('safe', 429, 'http', retry_after=120), 'unused'])
        with self.assertRaises(GeminiError): pool.generate('next')
        self.assertEqual(self.calls, ['synthetic-private-key-1'])
        self.assertEqual(pool.status()['active'], 2)
        reopened = self.pool(['unused']*3, Vault(self.vault.path))
        with self.assertRaises(GeminiError): reopened.generate('restart')
        self.assertEqual(len(self.calls), 1)

    def test_timeout_request_content_and_billing_never_switch(self):
        for error in (GeminiError('hidden', kind='timeout'), GeminiError('hidden', kind='network'),
                      GeminiError('hidden', 400, 'http'), GeminiError('hidden', 403, 'http'),
                      GeminiError('hidden', 402, 'http'), GeminiError('hidden', 401, 'http', reason='BILLING_DISABLED'),
                      GeminiError('hidden', 500, 'http')):
            self.calls.clear()
            pool = self.pool([error, 'unused', 'unused'])
            with self.assertRaises(GeminiError): pool.generate('question')
            self.assertEqual(self.calls, ['synthetic-private-key-0'])
            self.assertEqual(pool.status()['active'], 1)

    def test_failover_announcement_after_backup_network_failure_and_restart(self):
        pool = self.pool([GeminiError('safe', 401, 'http'), GeminiError('safe', kind='network'), 'unused'])
        with self.assertRaises(GeminiError): pool.generate('first')
        self.assertNotIn('Đã chuyển sang API dự phòng #2', self.messages)
        reopened = self.pool(['unused', 'answer', 'unused'], Vault(self.vault.path))
        reopened.generate('next-new-question')
        self.assertIn('Đã chuyển sang API dự phòng #2', self.messages)
        self.assertEqual(reopened.status()['active_status'], 'generation_verified')

    def test_status_indices_and_wait_only(self):
        pool = self.pool(['a','b','c'])
        text = status_text({'window_times': [], 'local_until': 0}, 150, now=100, key_status=pool.status())
        self.assertIn('API đang chọn #1', text)
        self.assertIn('#2=not_checked', text)
        self.assertIn('50s', text)
        self.assertNotIn('synthetic-private-key', text)


class ReconnectTests(unittest.TestCase):
    def test_read_recovers_after_network_timeout_without_send(self):
        calls, delays = [], []
        def read():
            calls.append('getUpdates')
            if len(calls) < 3: raise APIError('private', kind='network')
            return {'read': 'ok'}
        result = read_with_reconnect(read, output=lambda _: None, pause=lambda d: delays.append(d) or True)
        self.assertEqual(result, {'read': 'ok'})
        self.assertEqual(delays, [5, 10]); self.assertEqual(calls, ['getUpdates']*3)

    def test_tls_auth_and_api_errors_do_not_retry(self):
        for error in (APIError('secret', kind='tls'), APIError('secret', 401, 'http'),
                      APIError('secret', 408, 'api'), APIError('secret', 400, 'http')):
            with self.assertRaises(APIError):
                read_with_reconnect(lambda: (_ for _ in ()).throw(error), pause=lambda _: self.fail('retried'))
        self.assertTrue(retryable({'kind': 'http', 'code': 503}))
        self.assertFalse(wait(10, quit_now=lambda: True, sleep=lambda _: self.fail('slept')))

    def test_read_wait_honors_quit(self):
        with self.assertRaises(KeyboardInterrupt):
            read_with_reconnect(lambda: (_ for _ in ()).throw(APIError('hidden', kind='timeout')),
                                output=lambda _: None, pause=lambda _: False)

    def test_safe_audit_excludes_secrets_and_rotates(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            record('result', folder=folder, active=2, outcome='sent', key='secret-key', message='secret-content')
            text = (folder/'ai_audit.jsonl').read_text(encoding='utf-8')
            self.assertNotIn('secret', text)
            (folder/'ai_audit.jsonl').write_bytes(b' '*1048577)
            record('poll_wait', folder=folder, kind='network', seconds=5)
            self.assertTrue((folder/'ai_audit.previous.jsonl').exists())
            self.assertLess((folder/'ai_audit.jsonl').stat().st_size, 1000)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.source, self.target = self.root/'source', self.root/'target'; self.source.mkdir()
        sample = {'event_name': 'message.text.received', 'message': {'text': TRIGGER+' private question',
                  'chat': {'id': 'synthetic-group', 'chat_type': 'GROUP'}}}
        (self.source/GROUP_SAMPLE).write_bytes(protect(json.dumps(sample).encode()))
        db = State(self.source/'one_shot.db')
        try:
            db.reserve(hashed('synthetic-bot'), APPROVAL)
            db.mark(hashed('synthetic-bot'), APPROVAL, 'api_acknowledged:synthetic-id')
        finally: db.close()
        state = State(self.source/'ai_reply.db')
        try:
            engine = ManagedResponder(state, 'synthetic-bot', 'synthetic-group', clock=lambda: 1000)
            for _ in range(10): engine._claim_ai()
            state.reserve(engine.group_key, 'already-processed')
        finally: state.close()
        self.archive = self.root/'transfer.zip'
    def tearDown(self): self.temp.cleanup()
    def test_transfer_reencrypts_group_preserves_limits_receipt_and_dedup(self):
        export_profile(self.source, self.archive)
        with zipfile.ZipFile(self.archive) as z:
            self.assertEqual(set(z.namelist()), {'profile.json', 'ai_reply.db', 'one_shot.db'})
            self.assertNotIn(b'private question', z.read('profile.json'))
        import_profile(self.archive, self.target)
        self.assertEqual(verified_group(self.target, 'synthetic-bot'), 'synthetic-group')
        self.assertNotEqual((self.source/GROUP_SAMPLE).read_bytes(), (self.target/GROUP_SAMPLE).read_bytes())
        state = State(self.target/'ai_reply.db')
        try:
            engine = ManagedResponder(state, 'synthetic-bot', 'synthetic-group', clock=lambda: 1001)
            self.assertEqual(engine.status()['remaining'], 0)
            self.assertEqual(engine.status()['local_until'], 1300)
            self.assertFalse(state.reserve(engine.group_key, 'already-processed'))
        finally: state.close()
        with self.assertRaises(ValueError): verified_group(self.target, 'wrong-bot')

    def test_import_never_overwrites_existing_state(self):
        export_profile(self.source, self.archive); import_profile(self.archive, self.target)
        old = (self.target/'ai_reply.db').read_bytes()
        with self.assertRaises(FileExistsError): import_profile(self.archive, self.target)
        self.assertEqual((self.target/'ai_reply.db').read_bytes(), old)
        with self.assertRaises(FileExistsError): export_profile(self.source, self.archive)

    def test_wrong_contents_and_dpapi_failure_leave_no_installed_db(self):
        with zipfile.ZipFile(self.archive, 'w') as z: z.writestr('../bad', 'bad')
        with self.assertRaises(ValueError): import_profile(self.archive, self.target)
        self.archive.unlink(); export_profile(self.source, self.archive)
        with patch('jat_design.portable_profile.protect', side_effect=OSError('hidden')):
            with self.assertRaises(OSError): import_profile(self.archive, self.target)
        self.assertFalse((self.target/'ai_reply.db').exists())
