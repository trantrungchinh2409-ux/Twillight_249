import contextlib
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, Mock
from jat_design import managed_ai as app
from jat_design import startup_check as sc
from jat_design.auto_reply import GROUP_SAMPLE, TRIGGER, hashed, Controls
from jat_design.key_vault import Vault
from jat_design.portable_profile import export_profile, import_profile
from jat_design.state import State
from jat_design.webhook_switch import protect


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.runtime = self.root/'runtime'; self.runtime.mkdir()
        self.prompt = self.root/'SYSTEM_PROMPT.txt'; self.prompt.write_text('Tra loi ngan.', encoding='utf-8')
        self.bot = 'synthetic-review-bot'
        sample = {'event_name': 'message.text.received', 'message': {'text': TRIGGER+' synthetic question',
                  'chat': {'id': 'synthetic-group', 'chat_type': 'GROUP'}}}
        (self.runtime/GROUP_SAMPLE).write_bytes(protect(json.dumps(sample).encode()))
        state = State(self.runtime/'one_shot.db')
        try:
            state.reserve(hashed(self.bot), 'approved-single-send-20261024')
            state.mark(hashed(self.bot), 'approved-single-send-20261024', 'api_acknowledged:synthetic')
        finally: state.close()
        state = State(self.runtime/'ai_reply.db'); state.close()
        Vault(self.runtime/'gemini_keys.dpapi').add('synthetic-private-key-never-log')
        self.messages = []
    def tearDown(self): self.temp.cleanup()
    def ready(self): return sc.ready(self.runtime, self.prompt, output=self.messages.append)
    def category(self, expected):
        code = self.ready()
        self.assertEqual(code, sc.ERRORS[expected][0]); self.assertIn(expected, str(self.messages))
        return code
    def test_valid_ready_is_read_only_and_does_not_call_api(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.runtime.iterdir()}
        with patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('network')):
            self.assertEqual(self.ready(), 0)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.runtime.iterdir()}
        self.assertEqual(before, after)
        self.assertNotIn('synthetic-private-key', str(self.messages))
        self.assertNotIn('synthetic-group', str(self.messages))
    def test_missing_receipt_db_is_specific_and_not_created(self):
        (self.runtime/'one_shot.db').unlink(); self.category('PROFILE_DB_MISSING')
        self.assertFalse((self.runtime/'one_shot.db').exists())
    def test_receipt_db_bad_schema_and_corruption(self):
        for data in (b'corrupt database', b''):
            (self.runtime/'one_shot.db').write_bytes(data); self.messages.clear()
            self.category('PROFILE_DB_READ')
    def test_missing_receipt_does_not_allow_start(self):
        db = sqlite3.connect(str(self.runtime/'one_shot.db'))
        db.execute('DELETE FROM deliveries'); db.commit(); db.close()
        self.category('PROFILE_RECEIPT')
    def test_missing_group_sample(self):
        (self.runtime/GROUP_SAMPLE).unlink(); self.category('PROFILE_SAMPLE_MISSING')
    def test_wrong_user_or_corrupt_dpapi_simulated_fails_closed(self):
        with patch.object(sc, 'protect', side_effect=OSError('secret-path-token-private')):
            self.category('PROFILE_DECRYPT')
        self.assertNotIn('secret-path-token-private', str(self.messages))
    def test_invalid_group_cannot_be_accepted(self):
        (self.runtime/GROUP_SAMPLE).write_bytes(protect(b'{"event_name":"wrong","message":{}}'))
        self.category('PROFILE_INVALID')
    def test_actual_token_must_match_receipt(self):
        with self.assertRaises(sc.StartupError) as result: sc.profile(self.runtime, 'wrong-bot')
        self.assertEqual(result.exception.category, 'PROFILE_INVALID')
    def test_missing_ai_db_not_reset_to_empty(self):
        (self.runtime/'ai_reply.db').unlink(); self.category('STATE_MISSING')
        self.assertFalse((self.runtime/'ai_reply.db').exists())
    def test_ai_db_corrupt_is_specific(self):
        (self.runtime/'ai_reply.db').write_bytes(b'not sqlite'); self.category('STATE_READ')
    def test_uncertain_guard_still_blocks_before_token(self):
        db = sqlite3.connect(str(self.runtime/'ai_reply.db'))
        db.execute('CREATE TABLE auto_block(k TEXT PRIMARY KEY,reason TEXT)')
        db.execute('INSERT INTO auto_block VALUES (?,?)', (hashed(self.bot),'send_pending_or_uncertain'))
        db.commit(); db.close(); self.category('SEND_UNCERTAIN')
    def test_incomplete_import_never_clears_marker(self):
        (self.runtime/'profile-import.pending').write_text('pending')
        self.category('IMPORT_PENDING'); self.assertTrue((self.runtime/'profile-import.pending').exists())
    def test_missing_empty_and_corrupt_vault(self):
        p = self.runtime/'gemini_keys.dpapi'; p.unlink(); self.category('VAULT_MISSING')
        vault = Vault(p); vault.save(); self.messages.clear(); self.category('VAULT_MISSING')
        p.write_bytes(b'synthetic-corrupt-dpapi'); self.messages.clear(); self.category('VAULT_READ')
    def test_write_permission_error_is_safe(self):
        with patch.object(sc.tempfile, 'mkstemp', side_effect=PermissionError('secret-path')):
            self.category('RUNTIME_WRITE')
        self.assertNotIn('secret-path', str(self.messages))
    def test_actual_locked_database_is_read_error_not_missing(self):
        db = sqlite3.connect(str(self.runtime/'one_shot.db')); db.execute('BEGIN EXCLUSIVE')
        try: self.category('PROFILE_DB_READ')
        finally: db.rollback(); db.close()
    def test_missing_prompt(self):
        self.prompt.unlink(); self.category('PROMPT')
    def run_main(self, **patches):
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(app, 'RUNTIME', self.runtime))
            stack.enter_context(patch('sys.argv', ['bot','--prompt',str(self.prompt)]))
            stack.enter_context(patch('sys.stdin.isatty', return_value=True))
            stack.enter_context(contextlib.redirect_stdout(output))
            stack.enter_context(patch('urllib.request.OpenerDirector.open', side_effect=AssertionError('NETWORK FORBIDDEN')))
            for name, value in patches.items(): stack.enter_context(patch.object(app,name,value))
            result = app.main()
        return result, output.getvalue()
    def test_missing_profile_stops_before_secret_prompt_or_network(self):
        (self.runtime/'one_shot.db').unlink(); hidden = Mock(side_effect=AssertionError('prompt'))
        code, text = self.run_main(hidden=hidden)
        self.assertEqual(code, 33); hidden.assert_not_called(); self.assertIn('PROFILE_DB_MISSING',text)
    def test_good_mock_startup_reaches_controls_without_poll_or_send(self):
        controls = Controls(); controls.command('QUIT')
        api = Mock(); api.getMe.return_value = self.bot
        with patch.object(app.threading, 'Thread'):
            code, text = self.run_main(hidden=Mock(return_value='synthetic-zalo-token'),
                Transport=Mock(), OfficialAPI=Mock(return_value=api), webhook_enabled=Mock(return_value=False),
                Controls=Mock(return_value=controls), receive_one=Mock(side_effect=AssertionError('poll')))
        self.assertEqual(code, 0); self.assertIn('ON / OFF / STATUS / QUIT',text)
        api.sendMessage.assert_not_called(); self.assertNotIn('synthetic-zalo-token',text)
    def test_vault_mutex_error_reports_stage_without_exception_text(self):
        class BadLock:
            def __init__(self, token): pass
            def __enter__(self): raise RuntimeError('secret-token-in-exception')
            def __exit__(self,*args): pass
        code, text = self.run_main(TokenLock=BadLock)
        self.assertEqual(code,41); self.assertIn('VAULT_LOCK',text); self.assertNotIn('secret-token',text)
    def test_imported_profile_is_ready_and_restart_keeps_ledger(self):
        target = self.root/'new-runtime'; transfer = self.root/'transfer.zip'
        source = State(self.runtime/'ai_reply.db')
        source.reserve('synthetic-hash', 'dedup-preserved'); source.close()
        export_profile(self.runtime, transfer); import_profile(transfer, target)
        Vault(target/'gemini_keys.dpapi').add('synthetic-new-target-key')
        for _ in range(2): self.assertEqual(sc.ready(target,self.prompt,output=lambda _:None),0)
        state = State(target/'ai_reply.db')
        try: self.assertFalse(state.reserve('synthetic-hash','dedup-preserved'))
        finally: state.close()

    def test_bot_mutex_failure_is_distinct_from_vault(self):
        real_lock = app.TokenLock
        def lock(token):
            if token == 'synthetic-zalo-token':
                class Bad:
                    def __enter__(self): raise RuntimeError('sensitive-token')
                    def __exit__(self,*args): pass
                return Bad()
            return real_lock(token)
        code, text = self.run_main(TokenLock=lock, hidden=Mock(return_value='synthetic-zalo-token'))
        self.assertEqual(code,42); self.assertIn('BOT_LOCK',text); self.assertNotIn('sensitive-token',text)

    def test_api_error_reports_stage_kind_and_code_without_raw_message(self):
        from jat_design.official_api import APIError
        api = Mock(); api.getMe.side_effect = APIError('private-token-url',403,'http')
        code, text = self.run_main(hidden=Mock(return_value='synthetic-zalo-token'),
            Transport=Mock(), OfficialAPI=Mock(return_value=api))
        self.assertEqual(code,1); self.assertIn('ZALO_INIT',text); self.assertIn('403',text)
        self.assertNotIn('private-token-url',text)

    def test_wrong_bot_after_getme_never_opens_poll_or_send(self):
        api = Mock(); api.getMe.return_value = 'wrong-bot'
        code, text = self.run_main(hidden=Mock(return_value='synthetic-zalo-token'),
            Transport=Mock(), OfficialAPI=Mock(return_value=api), webhook_enabled=Mock(return_value=False))
        self.assertEqual(code,38); self.assertIn('PROFILE_INVALID',text); api.sendMessage.assert_not_called()
