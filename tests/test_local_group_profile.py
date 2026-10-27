"""Synthetic offline transport/DPAPI doubles; never evidence of a real Zalo event."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch
from jat_design import local_group_profile as p
from jat_design import startup_check as sc
from jat_design.auto_reply import verified_group, TRIGGER, hashed
from jat_design.managed_limits import ManagedResponder
from jat_design.official_api import APIError
from jat_design.state import State


def test_protect(data, decrypt=False):
    # Deliberately a test double, NOT encryption or a replacement DPAPI provider.
    return base64.b64decode(data[9:]) if decrypt else b'TESTONLY:'+base64.b64encode(data)


def event(marker='JAT-VERIFY-'+'A'*32, stamp=1000000):
    return {'event_name':'message.text.received', 'message':{
        'chat':{'id':'synthetic-private-group', 'chat_type':'GROUP'},
        'from':{'id':'synthetic-user', 'is_bot':False},
        'text':TRIGGER+' '+marker, 'date':stamp, 'message_id':'synthetic-event'}}


class ReadAPI:
    def __init__(self, webhook=''):
        self.webhook = webhook; self.methods = []
    def post(self, method, payload, timeout):
        self.methods.append(method)
        if method=='getMe': return {'id':'synthetic-bot'}
        if method=='getWebhookInfo': return {'url':self.webhook}
        raise AssertionError('Unexpected method: '+method)


class LocalGroupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.runtime = self.root/'runtime'; self.runtime.mkdir()
        self.prompt = self.root/'prompt'; self.prompt.write_text('Synthetic prompt')
        self.patch = patch.object(p,'protect',side_effect=test_protect); self.patch.start()
        self.marker = 'JAT-VERIFY-'+'A'*32; self.bot = 'synthetic-bot'
    def tearDown(self): self.patch.stop(); self.temp.cleanup()
    def persist(self): return p.persist(self.runtime,self.bot,event(self.marker),self.marker,1000,now=1001)
    def test_launcher_exposes_registration_without_requiring_missing_profile(self):
        from jat_design import win7_python
        with patch.object(win7_python,'check',return_value=0),patch('sys.stdin.isatty',return_value=True),patch.object(p,'main',return_value=50) as register,patch.object(sc,'ready',side_effect=AssertionError('E33 must not block registration')):
            self.assertEqual(win7_python.main(['--verify-group']),50)
            register.assert_called_once_with()
    def test_redirected_secret_input_cannot_start_registration(self):
        with patch('sys.stdin.isatty',return_value=False),patch.object(p,'collect') as register:
            self.assertEqual(p.main(),2)
            register.assert_not_called()
    def test_schema_readonly_proof_and_restart_without_forged_send_ack(self):
        self.assertEqual(self.persist(),'synthetic-private-group')
        for _ in range(2):
            self.assertEqual(p.load_profile(self.runtime,self.bot),'synthetic-private-group')
            self.assertEqual(verified_group(self.runtime,self.bot),'synthetic-private-group')
            self.assertEqual(sc.profile(self.runtime,self.bot),'synthetic-private-group')
        with p.readonly(self.runtime/'one_shot.db') as db:
            rows=db.execute('SELECT event_id,status FROM deliveries').fetchall()
            self.assertEqual(rows[0][0],p.RECEIPT)
            self.assertFalse(any('api_acknowledged' in row[1] for row in rows))
            self.assertEqual(db.execute('SELECT count(*) FROM group_verifications').fetchone()[0],1)
        data=json.loads(test_protect((self.runtime/p.PROOF).read_bytes(),decrypt=True))
        self.assertFalse(data['messages_sent']);self.assertFalse(data['history_restored'])
        self.assertNotIn('text',data);self.assertNotIn('sender',data)
        self.assertNotIn('synthetic-user',str(data));self.assertNotIn('synthetic-event',str(data))
        self.assertNotIn(self.marker,str(data))
    def test_wrong_bot_and_changed_receipt_fail_closed(self):
        self.persist()
        with self.assertRaises(p.ProfileError): p.load_profile(self.runtime,'another-bot')
        with self.assertRaises(sc.StartupError): sc.profile(self.runtime,'another-bot')
        with sqlite3.connect(self.runtime/'one_shot.db') as db:
            db.execute("UPDATE deliveries SET status='api_acknowledged:fake'")
        with self.assertRaises(p.ProfileError): p.load_profile(self.runtime,self.bot)
        with self.assertRaises(sc.StartupError): sc.profile(self.runtime,self.bot)
    def test_encrypted_proof_missing_or_corrupt_never_falls_back_to_legacy(self):
        self.persist();(self.runtime/p.PROOF).write_bytes(b'corrupt')
        with self.assertRaises(p.ProfileError): verified_group(self.runtime,self.bot)
        with self.assertRaises(sc.StartupError): sc.profile(self.runtime,self.bot)
    def test_legacy_group_receipt_path_still_valid_without_local_profile(self):
        from jat_design.auto_reply import GROUP_SAMPLE
        from jat_design import auto_reply
        sample={'event_name':'message.text.received','message':{'chat':{'id':'legacy-group','chat_type':'GROUP'},'text':TRIGGER}}
        (self.runtime/GROUP_SAMPLE).write_bytes(test_protect(json.dumps(sample).encode()))
        state=State(self.runtime/'one_shot.db')
        state.reserve(hashed(self.bot),'approved-single-send-20261024')
        state.mark(hashed(self.bot),'approved-single-send-20261024','api_acknowledged:synthetic-unit-only')
        state.close();state=State(self.runtime/'ai_reply.db');state.close()
        with patch.object(sc,'protect',side_effect=test_protect),patch.object(auto_reply,'protect',side_effect=test_protect):
            self.assertEqual(sc.profile(self.runtime,self.bot),'legacy-group')
            self.assertEqual(verified_group(self.runtime,self.bot),'legacy-group')
    def test_deleted_local_proof_cannot_turn_readonly_row_into_legacy_send_approval(self):
        self.persist();(self.runtime/p.PROOF).unlink()
        with self.assertRaises(sc.StartupError) as error: sc.profile(self.runtime,self.bot)
        self.assertEqual(error.exception.category,'PROFILE_RECEIPT')
        with self.assertRaises(ValueError): verified_group(self.runtime,self.bot)
    def test_pending_marker_blocks_readiness_and_registration(self):
        self.persist();(self.runtime/p.PENDING).write_text('pending')
        with self.assertRaises(p.ProfileError): p.load_profile(self.runtime,self.bot)
        with self.assertRaises(sc.StartupError) as error: sc.profile(self.runtime)
        self.assertEqual(error.exception.category,'IMPORT_PENDING')
        with self.assertRaises(p.ProfileError): p.check_targets(self.runtime)
    def test_existing_profile_not_overwritten(self):
        self.persist(); before={f.name:f.read_bytes() for f in self.runtime.iterdir()}
        with self.assertRaises(p.ProfileError): self.persist()
        self.assertEqual(before,{f.name:f.read_bytes() for f in self.runtime.iterdir()})
    def test_uncertain_state_cannot_be_reset_by_registration(self):
        s=State(self.runtime/'ai_reply.db');engine=ManagedResponder(s,self.bot,'synthetic-private-group')
        s.db.execute('INSERT INTO auto_block VALUES (?,?)',(engine.bot_key,'uncertain'));s.db.commit();s.close()
        before=(self.runtime/'ai_reply.db').read_bytes()
        with self.assertRaises(p.ProfileError): self.persist()
        self.assertEqual(before,(self.runtime/'ai_reply.db').read_bytes())
        self.assertFalse((self.runtime/'one_shot.db').exists())
    def test_preserves_existing_dedup_counters_google_wait_and_vault(self):
        s=State(self.runtime/'ai_reply.db');engine=ManagedResponder(s,self.bot,'synthetic-private-group')
        s.reserve(engine.group_key,'old-dedup')
        s.db.execute('INSERT INTO ai_window_calls VALUES (?,?)',(engine.bot_key,999))
        s.db.execute('UPDATE ai_window_state SET local_until=1800,google_until=1900 WHERE bot=?',(engine.bot_key,))
        s.db.execute('INSERT INTO auto_limits VALUES (?,?)',(engine.group_key,1600));s.db.commit();s.close()
        vault=self.runtime/'gemini_keys.dpapi';vault.write_bytes(b'existing-private-encrypted-vault')
        before=vault.read_bytes();self.persist();self.assertEqual(before,vault.read_bytes())
        s=State(self.runtime/'ai_reply.db');engine=ManagedResponder(s,self.bot,'synthetic-private-group',clock=lambda:1001)
        self.assertFalse(s.reserve(engine.group_key,'old-dedup'))
        row=s.db.execute('SELECT local_until,google_until FROM ai_window_state').fetchone()
        self.assertEqual(row,(1800,1900));self.assertEqual(engine.status()['cooldown_until'],1600)
        self.assertEqual(engine.status()['window_times'],[999]);s.close()
    def test_new_history_is_explicitly_empty_with_conservative_pause_and_nonce_dedup(self):
        self.persist();s=State(self.runtime/'ai_reply.db')
        engine=ManagedResponder(s,self.bot,'synthetic-private-group',clock=lambda:1001)
        self.assertEqual(engine.status()['local_until'],1301)
        self.assertEqual(engine.status()['remaining'],0)
        self.assertEqual(engine.status()['window_times'],[])
        self.assertFalse(s.reserve(engine.group_key,hashed('synthetic-event')))
        api,pool=Mock(),Mock()
        self.assertEqual(engine.handle(api,pool,event(self.marker),True,1000000),'duplicate')
        api.sendMessage.assert_not_called();pool.generate.assert_not_called();s.close()
    def test_rejects_wrong_group_type_sender_nonce_old_or_future_date(self):
        cases=[]
        for field,value in [('chat_type','PRIVATE')]:
            e=event();e['message']['chat'][field]=value;cases.append(e)
        for value in (True,None):
            e=event();e['message']['from']['is_bot']=value;cases.append(e)
        e=event();e['message']['from']['id']=self.bot;cases.append(e)
        e=event('another-marker');cases.append(e)
        e=event(stamp=999000);cases.append(e)
        for stamp in (None,True,float('nan'),float('inf'),1100000): cases.append(event(stamp=stamp))
        for e in cases:
            self.assertFalse(p.eligible(e,self.bot,self.marker,1000,1001))
            with self.assertRaises(p.ProfileError): p.persist(self.runtime,self.bot,e,self.marker,1000,now=1001)
        self.assertFalse((self.runtime/'one_shot.db').exists())
    def test_partial_write_failure_keeps_guard_and_never_reports_ready(self):
        with patch('jat_design.managed_limits.ManagedResponder',side_effect=RuntimeError('disk fault')):
            with self.assertRaises(RuntimeError): self.persist()
        self.assertTrue((self.runtime/p.PENDING).exists())
        with self.assertRaises(sc.StartupError) as error: sc.profile(self.runtime)
        self.assertEqual(error.exception.category,'IMPORT_PENDING')
    def receiver(self, read, **kwargs):
        # Obtain the nonce from the predicate closure only inside this synthetic test.
        nonce=next(c.cell_contents for c in kwargs['accept'].__closure__ if isinstance(c.cell_contents,str) and c.cell_contents.startswith('JAT-VERIFY-'))
        e=event(nonce,stamp=1000000)
        self.assertTrue(kwargs['accept'](e))
        for method in ('sendMessage','setWebhook','deleteWebhook','testWebhook'):
            with self.assertRaises(ValueError): read.post(method,{},1)
        return e
    def test_readonly_collection_confirmation_and_safe_console(self):
        api=ReadAPI();output=[]
        self.assertEqual(p.collect(api,self.runtime,confirm=lambda _: 'XAC NHAN',receiver=self.receiver,
                                   clock=lambda:1000,output=output.append),0)
        self.assertEqual(api.methods,['getMe','getWebhookInfo'])
        text=' '.join(output)
        for value in ('synthetic-private-group','synthetic-user','synthetic-event'):
            self.assertNotIn(value,text)
        self.assertIn('Messages sent=0',text)
    def test_existing_polling_loop_receives_group_through_only_read_api_methods(self):
        class PollAPI(ReadAPI):
            def post(api, method, payload, timeout):
                if method == 'getUpdates':
                    api.methods.append(method)
                    self.assertEqual(payload, {'timeout':'30'})
                    return event(self.marker, stamp=1000000)
                return super(PollAPI, api).post(method, payload, timeout)
        api=PollAPI()
        with patch.object(p.secrets,'token_hex',return_value='A'*32):
            self.assertEqual(p.collect(api,self.runtime,confirm=lambda _: 'XAC NHAN',
                                      clock=lambda:1000,output=lambda _:None),0)
        self.assertEqual(api.methods,['getMe','getWebhookInfo','getUpdates'])
        self.assertEqual(p.load_profile(self.runtime,self.bot),'synthetic-private-group')
    def test_first_poll_api_error_stops_without_profile_or_mutation(self):
        class BadAPI(ReadAPI):
            def post(api, method, payload, timeout):
                if method == 'getUpdates':
                    api.methods.append(method)
                    raise APIError('private-token-request-description',403,'http')
                return super(BadAPI, api).post(method,payload,timeout)
        api=BadAPI();outputs=[]
        with self.assertRaises(p.ProfileError):
            p.collect(api,self.runtime,confirm=lambda _: 'XAC NHAN',clock=lambda:1000,output=outputs.append)
        self.assertEqual(api.methods,['getMe','getWebhookInfo','getUpdates'])
        self.assertEqual(list(self.runtime.iterdir()),[])
        self.assertNotIn('private-token-request-description',' '.join(outputs))
    def test_cancel_timeout_and_webhook_do_not_create_files(self):
        with self.assertRaises(p.ProfileError):
            p.collect(ReadAPI(),self.runtime,confirm=lambda _: '',receiver=self.receiver,clock=lambda:1000,output=lambda _:None)
        self.assertEqual(list(self.runtime.iterdir()),[])
        with self.assertRaises(p.ProfileError):
            p.collect(ReadAPI(),self.runtime,receiver=lambda *a,**k:None,output=lambda _:None)
        self.assertEqual(list(self.runtime.iterdir()),[])
        receiver=Mock(side_effect=AssertionError('must not poll'))
        with self.assertRaises(p.ProfileError): p.collect(ReadAPI(webhook='https://private.example'),self.runtime,receiver=receiver)
        receiver.assert_not_called();self.assertEqual(list(self.runtime.iterdir()),[])
    def test_offline_check_ready_without_vault_calls_no_api_and_writes_no_user_data(self):
        self.persist();before={f.name:f.read_bytes() for f in self.runtime.iterdir()}
        with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network')):
            self.assertEqual(sc.ready(self.runtime,self.prompt,require_vault=False,output=lambda _:None),0)
        self.assertEqual(before,{f.name:f.read_bytes() for f in self.runtime.iterdir()})


@unittest.skipUnless(os.name=='nt','Native Windows DPAPI required; not replaced by mock acceptance')
class NativeProfileTests(unittest.TestCase):
    def test_real_dpapi_profile_roundtrip_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime=Path(temp);nonce='JAT-VERIFY-'+'A'*32
            with patch('urllib.request.OpenerDirector.open',side_effect=AssertionError('network')):
                p.persist(runtime,'synthetic-bot',event(nonce),nonce,1000,now=1001)
                self.assertEqual(p.load_profile(runtime,'synthetic-bot'),'synthetic-private-group')
                self.assertNotIn(b'synthetic-private-group',(runtime/p.PROOF).read_bytes())
