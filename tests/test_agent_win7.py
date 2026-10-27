"""Offline fixtures only; test DPAPI double is never a live identity or crypto claim."""
import base64
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock,patch
from jat_design.agent_store import AgentStore,ALIASES
from jat_design.agent_engine import AgentService,AgentControls,GuardedResponder
from jat_design.agent_gemini import AgentPrompt,ConversationGemini
from jat_design.agent_transport import AgentTransport
from jat_design.agent_names import capture_alias
from jat_design.state import State
from jat_design.auto_reply import TRIGGER,hashed
from jat_design.gemini_client import GeminiError,PREFERRED
from jat_design.key_vault import KeyPool


def double(data,decrypt=False):
    return base64.b64decode(data[9:]) if decrypt else b'TESTONLY:'+base64.b64encode(data)


class Clock:
    def __init__(self):self.wall=1700000000.;self.mono=0.;self.callback=None
    def now(self):return self.wall
    def monotonic(self):return self.mono
    def sleep(self,n):
        self.wall+=n;self.mono+=n
        if self.callback:self.callback()
    def advance(self,n):self.sleep(n)


class Pool:
    def __init__(self,clock=None):self.calls=[];self.clock=clock;self.on_generate=None;self.error=None
    def wait_remaining(self):return 0
    def status(self):return {'active':1}
    def generate(self,question):
        self.calls.append(question)
        if self.on_generate:self.on_generate()
        if self.error:raise self.error
        return 'Câu trả lời thử nghiệm.'


class API:
    def __init__(self,clock):self.clock=clock;self.sent=[];self.actions=[];self.timeout=False
    def typing(self,group):self.actions.append(group);return True
    def sendMessage(self,group,answer):
        self.sent.append((self.clock.monotonic(),group,answer))
        if self.timeout:raise TimeoutError('private-URL-token')
        return {'message_id':'synthetic-ack-'+str(len(self.sent))}


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.patch=patch('jat_design.agent_store.protect',side_effect=double);self.patch.start()
        self.clock=Clock();self.store=AgentStore(self.root/'agent.db',self.clock.now)
        self.state=State(self.root/'ai_reply.db');self.bot='synthetic-bot';self.group='synthetic-group'
        self.controls=AgentControls(self.clock.now);self.controls.command('ON');self.controls.command('AGENT ON')
        self.service=AgentService(self.state,self.store,self.bot,self.group,self.clock.now,self.clock.monotonic,self.clock.sleep)
        self.api=API(self.clock);self.pool=Pool(self.clock);self.serial=0
    def tearDown(self):self.store.close();self.state.close();self.patch.stop();self.tmp.cleanup()
    def event(self,sender='A',text=None):
        self.serial+=1
        return {'event_name':'message.text.received','message':{'chat':{'id':self.group,'chat_type':'GROUP'},
            'from':{'id':sender,'is_bot':False},'message_id':str(self.serial),'date':self.clock.now()*1000,
            'text':TRIGGER+' câu hỏi' if text is None else text}}
    def process(self,e,service=None):
        snap=self.controls.snapshot()
        return (service or self.service).process(self.api,self.pool,e,snap,lambda:self.controls.valid(snap),self.clock.monotonic())
    def test_three_interleaved_members_keep_real_identity_names_and_private_context(self):
        aliases=['AI JAT','KHẢI LÒ XO','LÊ KHẢI GIÁP']
        for sender,alias in zip('ABC',aliases):self.store.bind(self.bot,self.group,sender,alias)
        events=[self.event(sender,TRIGGER+' câu hỏi '+sender) for sender in 'ABC']
        for e in events:self.assertEqual(self.process(e),'sent')
        self.assertEqual(len(self.api.sent),3)
        for i,alias in enumerate(aliases):
            self.assertTrue(self.api.sent[i][2].startswith(alias+', '))
            self.assertEqual(self.pool.calls[i].alias,alias);self.assertEqual(self.pool.calls[i].history,[])
        self.clock.advance(13)
        self.assertEqual(self.process(self.event('A',TRIGGER+' tiếp A')),'sent')
        self.assertEqual(len(self.pool.calls[-1].history),1)
        self.assertEqual(self.pool.calls[-1].history[0][0],'câu hỏi A')
        self.assertNotIn('câu hỏi B',str(self.pool.calls[-1].history))
    def test_live_raw_reply_metadata_is_not_guessed_and_no_session_member_is_ignored(self):
        self.assertEqual(self.process(self.event('B','nói chuyện thường')),'no_session')
        self.assertEqual(self.process(self.event('A')),'sent');self.clock.advance(13)
        e=self.event('A','Hà Nội nhé');e['message']['reply_to_message']={'from':{'id':self.bot}}
        self.assertEqual(self.process(e),'reply_metadata_unverified')
        self.assertEqual(len(self.api.sent),1)
    def test_offline_verified_adapter_supports_followup_and_requires_addressing(self):
        service=AgentService(self.state,self.store,self.bot,self.group,self.clock.now,self.clock.monotonic,self.clock.sleep,
                             reply_adapter=lambda e,b:e['message'].get('normalized_test_reply_to_bot'))
        self.assertEqual(self.process(self.event('A'),service),'sent');self.clock.advance(13)
        self.assertEqual(self.process(self.event('A','nói với người khác'),service),'not_addressed')
        e=self.event('A','Hà Nội nhé');e['message']['normalized_test_reply_to_bot']=True
        self.assertEqual(self.process(e,service),'sent')
        self.assertEqual(self.pool.calls[-1].question,'Hà Nội nhé');self.assertEqual(len(self.pool.calls[-1].history),1)
    def test_sender_followup_does_not_depend_on_reply_metadata_when_manager_opts_in(self):
        self.store.bind(self.bot,self.group,'A','AI JAT')
        self.assertEqual(self.process(self.event('A')),'sent');self.clock.advance(13)
        self.controls.command('FOLLOWUP ON XAC NHAN')
        self.assertEqual(self.process(self.event('B','nói chuyện xen kẽ')),'no_session')
        self.assertEqual(self.process(self.event('A','Hà Nội nhé')),'sent')
        self.assertIsNone(self.service.reply_adapter)
        self.assertEqual(self.pool.calls[-1].question,'Hà Nội nhé');self.assertEqual(len(self.pool.calls[-1].history),1)
        self.controls.command('FOLLOWUP OFF');self.clock.advance(13)
        self.assertEqual(self.process(self.event('A','nói với người khác')),'reply_metadata_unverified')
    def test_verified_address_to_other_member_has_priority_over_opt_in_catchall(self):
        service=AgentService(self.state,self.store,self.bot,self.group,self.clock.now,self.clock.monotonic,self.clock.sleep,
                             reply_adapter=lambda e,b:e['message'].get('normalized_test_reply_to_bot'))
        self.process(self.event('A'),service);self.clock.advance(13);self.controls.command('FOLLOWUP ON XAC NHAN')
        e=self.event('A','câu nói với B');e['message']['normalized_test_reply_to_bot']=False
        self.assertEqual(self.process(e,service),'addressed_to_other');self.assertEqual(len(self.pool.calls),1)
    def test_memory_clear_cancels_current_job_without_removing_names_or_counters(self):
        self.store.bind(self.bot,self.group,'A','AI JAT')
        self.pool.on_generate=lambda:self.controls.command('MEMORY CLEAR')
        self.assertEqual(self.process(self.event()),'off');self.assertEqual(self.api.sent,[])
        self.assertTrue(self.controls.take_clear());self.store.clear()
        self.assertEqual(self.store.count(self.bot,self.group),0)
        self.assertEqual(self.store.alias(self.bot,self.group,'A'),'AI JAT')
        self.assertEqual(self.service.engine.status()['remaining'],9)
    def test_aliases_survive_restart_but_never_infer_identity_from_name(self):
        self.store.bind(self.bot,self.group,'A','AI JAT');self.store.close()
        self.store=AgentStore(self.root/'agent.db',self.clock.now)
        self.assertEqual(self.store.alias(self.bot,self.group,'A'),'AI JAT')
        self.assertEqual(self.store.alias(self.bot,self.group,'AI JAT'),'bạn')
    def test_expired_session_removed_without_removing_alias(self):
        self.store.bind(self.bot,self.group,'A','AI JAT');self.process(self.event())
        self.clock.advance(301);self.store.prune()
        self.assertFalse(self.store.active(self.bot,self.group,'A'))
        self.assertEqual(self.store.alias(self.bot,self.group,'A'),'AI JAT')
        self.assertEqual(self.store.count(self.bot,self.group),0)
    def test_session_stores_at_most_six_pairs_and_survives_restart_only_until_expiry(self):
        for i in range(7):
            self.assertEqual(self.process(self.event('A',TRIGGER+' q'+str(i))),'sent');self.clock.advance(13)
        history=self.store.session(self.bot,self.group,'A')['history']
        self.assertEqual(len(history),6);self.assertEqual(history[0][0],'q1')
        self.store.close();self.store=AgentStore(self.root/'agent.db',self.clock.now)
        self.assertEqual(self.store.session(self.bot,self.group,'A')['history'],history)
        self.clock.advance(301);self.store.prune();self.assertIsNone(self.store.session(self.bot,self.group,'A'))
    def test_self_wrong_group_private_and_wrong_sender_flags_are_ignored(self):
        for mutate in [lambda e:e['message']['from'].update(id=self.bot),lambda e:e['message']['chat'].update(id='other'),
                       lambda e:e['message']['chat'].update(chat_type='PRIVATE'),lambda e:e['message']['from'].update(is_bot=True)]:
            e=self.event();mutate(e);self.assertEqual(self.process(e),'ignored')
        self.assertEqual(self.api.sent,[]);self.assertEqual(self.pool.calls,[])
    def test_delay_2_5_seconds_and_slow_model_sends_as_soon_as_result_available(self):
        self.assertEqual(self.process(self.event()),'sent');self.assertAlmostEqual(self.api.sent[0][0],2.5,places=4)
        self.clock.advance(13);start=self.clock.monotonic();self.pool.on_generate=lambda:self.clock.advance(4)
        self.assertEqual(self.process(self.event('B')),'sent');self.assertAlmostEqual(self.api.sent[-1][0]-start,4,places=4)
        self.assertEqual(len(self.api.actions),2)
    def test_off_during_delay_discards_answer_without_false_uncertain_guard(self):
        self.clock.callback=lambda:self.controls.command('OFF')
        self.assertEqual(self.process(self.event()),'off')
        self.assertEqual(self.api.sent,[]);self.assertFalse(self.service.engine.blocked())
        self.assertEqual(self.store.session(self.bot,self.group,'A')['history'],[])
    def test_off_then_on_during_generation_does_not_revive_old_answer(self):
        def toggle():self.controls.command('OFF');self.controls.command('ON')
        self.pool.on_generate=toggle
        self.assertEqual(self.process(self.event()),'off');self.assertEqual(self.api.sent,[])
    def test_agent_off_cancels_agent_jobs_but_basic_bot_remains_independent(self):
        self.pool.on_generate=lambda:self.controls.command('AGENT OFF')
        self.assertEqual(self.process(self.event()),'off');self.assertTrue(self.controls.snapshot()['bot'])
        self.pool.on_generate=None;self.clock.advance(13)
        self.assertEqual(self.process(self.event('B')),'sent')
        self.assertIsInstance(self.pool.calls[-1],str)
        self.assertIsNone(self.store.session(self.bot,self.group,'B'))
    def test_uncertain_send_is_durable_and_never_retried_after_restart(self):
        self.api.timeout=True;e=self.event()
        self.assertEqual(self.process(e),'uncertain_blocked');self.assertTrue(self.service.engine.blocked())
        self.state.close();self.state=State(self.root/'ai_reply.db')
        service=AgentService(self.state,self.store,self.bot,self.group,self.clock.now,self.clock.monotonic,self.clock.sleep)
        self.clock.advance(13);self.assertEqual(self.process(self.event('B'),service),'uncertain_blocked')
        self.assertEqual(len(self.api.sent),1);self.assertEqual(self.store.session(self.bot,self.group,'A')['history'],[])
    def test_duplicate_event_never_calls_model_or_sends_twice(self):
        e=self.event();self.assertEqual(self.process(e),'sent');self.clock.advance(13)
        self.assertEqual(self.process(e),'duplicate');self.assertEqual(len(self.pool.calls),1)
    def test_tenth_ai_budget_slot_can_send_then_pause_prevents_new_model_calls(self):
        for i in range(10):self.assertEqual(self.process(self.event('U'+str(i))),'sent')
        self.assertEqual(len(self.pool.calls),10)
        outcome=self.process(self.event('extra'))
        self.assertIn(outcome,('notice_sent','internal_wait'))
        self.assertEqual(len(self.pool.calls),10);self.assertGreater(self.service.engine.status()['local_until'],self.clock.now())
    def test_google_429_wait_and_no_history_answer_or_automatic_retry(self):
        self.pool.error=GeminiError('private-provider-body',429,'http',retry_after=90)
        self.assertEqual(self.process(self.event()),'google_wait')
        self.assertEqual(self.api.sent,[]);self.assertEqual(self.store.session(self.bot,self.group,'A')['history'],[])
        self.clock.advance(13);self.assertEqual(self.process(self.event('B')),'google_wait');self.assertEqual(len(self.pool.calls),1)
    def test_end_and_clear_are_scoped_and_old_command_cannot_clear_new_session(self):
        self.process(self.event('A'));self.process(self.event('B'));self.clock.advance(13)
        command=self.event('A',TRIGGER+' /clear');self.assertEqual(self.process(command),'session_ended')
        self.assertIsNone(self.store.session(self.bot,self.group,'A'));self.assertIsNotNone(self.store.session(self.bot,self.group,'B'))
        self.assertEqual(self.process(self.event('A')),'sent')
        self.assertEqual(self.process(command),'duplicate');self.assertIsNotNone(self.store.session(self.bot,self.group,'A'))
    def test_alias_conflict_requires_explicit_unbind_and_rename_confirmation(self):
        self.store.bind(self.bot,self.group,'A','AI JAT')
        with self.assertRaises(ValueError):self.store.bind(self.bot,self.group,'B','AI JAT')
        with self.assertRaises(ValueError):self.store.bind(self.bot,self.group,'A','new alias')
        self.store.bind(self.bot,self.group,'A','new alias',replace=True)
        self.assertEqual(self.store.alias(self.bot,self.group,'B'),'bạn')
    def test_identity_and_history_never_mix_across_groups_or_bots(self):
        self.store.bind(self.bot,self.group,'A','AI JAT');self.process(self.event())
        self.assertEqual(self.store.alias(self.bot,'other-group','A'),'bạn')
        self.assertIsNone(self.store.session('other-bot',self.group,'A'))
    def test_controls_defaults_off_and_catchall_has_no_live_bypass(self):
        c=AgentControls();self.assertFalse(c.snapshot()['bot']);self.assertFalse(c.snapshot()['agent'])
        self.assertTrue(c.command('CATCHALL ON').startswith('CONFIRM_REQUIRED'));self.assertFalse(c.snapshot()['catchall'])
        c.command('FOLLOWUP ON XAC NHAN');self.assertTrue(c.snapshot()['catchall'])
        c.command('FOLLOWUP OFF');self.assertFalse(c.snapshot()['catchall'])
    def test_queue_older_than_60_seconds_dropped_without_provider_call(self):
        e=self.event();snap=self.controls.snapshot()
        self.assertEqual(self.service.process(self.api,self.pool,e,snap,lambda:True,-61),'queue_expired')
        self.assertEqual(self.pool.calls,[])
    def test_known_pre_send_cancel_is_not_misclassified_as_http_timeout(self):
        key=hashed('event');self.state.reserve(self.service.engine.group_key,key)
        checks=iter([True,False])
        outcome=self.service.engine._send(self.api,'answer',key,lambda:next(checks))
        self.assertEqual(outcome,'off');self.assertFalse(self.service.engine.blocked());self.assertEqual(self.api.sent,[])
    def test_agent_does_not_modify_profile_database(self):
        profile=self.root/'one_shot.db';profile.write_bytes(b'untouched accepted private profile')
        before=profile.read_bytes();self.process(self.event());self.assertEqual(profile.read_bytes(),before)


class Response:
    def __init__(self,body):self.body=json.dumps(body).encode()
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,limit):return self.body[:limit]


class AdapterTests(unittest.TestCase):
    def test_addon_checks_accepted_base_without_modifying_it(self):
        from run_agent_win7 import verify_base,main
        import run_agent_win7
        root=Path(__file__).resolve().parents[1]
        self.assertTrue(verify_base(root))
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp);self.assertFalse(verify_base(base))
            with patch.object(run_agent_win7,'BASE',base):self.assertEqual(main(['--check']),60)
            self.assertEqual(list(base.iterdir()),[])
    def test_gemini_keeps_system_prompt_and_only_given_person_history(self):
        requests=[]
        class Opener:
            def open(self,request,timeout):
                requests.append(request)
                return Response({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'OK'}]}}]})
        c=ConversationGemini('synthetic-private-key','UNCHANGED SYSTEM',Opener());c.model=PREFERRED[0]
        self.assertEqual(c.generate(AgentPrompt('new A',[['old A','answer A']],'AI JAT')),'OK')
        body=json.loads(requests[0].data)
        self.assertTrue(body['systemInstruction']['parts'][0]['text'].startswith('UNCHANGED SYSTEM\n'))
        self.assertEqual([m['role'] for m in body['contents']],['user','model','user'])
        self.assertNotIn('old B',str(body));self.assertIn('AI JAT',str(body));self.assertIsNone(c.turn)
    def test_typing_uses_official_post_and_never_placeholder_or_token_in_error(self):
        calls=[]
        class Opener:
            def open(self,request,timeout):calls.append((request,timeout));return Response({'ok':True})
        t=AgentTransport('synthetic/token',Opener());self.assertTrue(t.typing('synthetic-group'))
        r,timeout=calls[0];self.assertTrue(r.full_url.endswith('/sendChatAction'))
        self.assertEqual(json.loads(r.data),{'chat_id':'synthetic-group','action':'typing'});self.assertEqual(timeout,2)
        class Fail:
            def open(self,*args,**kwargs):raise TimeoutError('private-token-url')
        self.assertFalse(AgentTransport('synthetic',Fail()).typing('synthetic-group'))
    def test_name_assignment_requires_actual_group_event_and_manager_confirmation(self):
        with tempfile.TemporaryDirectory() as temp,patch('jat_design.agent_store.protect',side_effect=double):
            store=AgentStore(Path(temp)/'agent.db',lambda:1000);outputs=[]
            nonce='JAT-NAME-'+'A'*32
            def receiver(read,**kwargs):
                e={'event_name':'message.text.received','message':{'chat':{'id':'g','chat_type':'GROUP'},'from':{'id':'real-api-member','is_bot':False},
                    'message_id':'real-api-event','date':1000000,'text':TRIGGER+' '+nonce}}
                self.assertTrue(kwargs['accept'](e));return e
            with patch('jat_design.agent_names.secrets.token_hex',return_value='A'*32):
                self.assertFalse(capture_alias(Mock(),'bot','g','AI JAT',store,confirm=lambda _: '',receiver=receiver,clock=lambda:1000,output=outputs.append))
                self.assertFalse(store.bound('bot','g','AI JAT'))
                self.assertTrue(capture_alias(Mock(),'bot','g','AI JAT',store,confirm=lambda _: 'XAC NHAN',receiver=receiver,clock=lambda:1000,output=outputs.append))
            self.assertEqual(store.alias('bot','g','real-api-member'),'AI JAT');self.assertNotIn('real-api-member',' '.join(outputs));store.close()
    def test_alias_capture_rejects_wrong_group_and_never_guesses_from_display_name(self):
        with tempfile.TemporaryDirectory() as temp,patch('jat_design.agent_store.protect',side_effect=double):
            store=AgentStore(Path(temp)/'agent.db',lambda:1000)
            def receiver(read,**kwargs):
                e={'event_name':'message.text.received','message':{'chat':{'id':'WRONG','chat_type':'GROUP'},'from':{'id':'sender','is_bot':False,'display_name':'AI JAT'},
                     'message_id':'event','date':1000000,'text':TRIGGER+' JAT-NAME-'+'A'*32}}
                self.assertFalse(kwargs['accept'](e));return e
            with patch('jat_design.agent_names.secrets.token_hex',return_value='A'*32):
                self.assertFalse(capture_alias(Mock(),'bot','g','AI JAT',store,confirm=lambda _: 'XAC NHAN',receiver=receiver,clock=lambda:1000,output=lambda _:None))
            self.assertFalse(store.bound('bot','g','AI JAT'));store.close()
    def test_existing_key_pool_failover_preserves_turn_without_rotating_on_429(self):
        class VaultDouble:
            def __init__(self):
                self.data={'items':[{'id':'one','key':'one','status':'not_checked'},{'id':'two','key':'two','status':'not_checked'}], 'primary':'one'}
                self.wait=0
            def wait_remaining(self):return self.wait
            def ordered(self):return list(self.data['items'])
            def save(self):pass
            def mark(self,item,status,code=None):item['status']=status
            def quota_wait(self,error):self.wait=90
        calls=[];question=AgentPrompt('A question',[['old A','answer A']],'AI JAT')
        class Factory:
            quota=False
            def __init__(self,key,prompt):self.key=key
            def generate(self,q):
                calls.append((self.key,q))
                if self.key=='one':raise GeminiError('private',429 if self.quota else 401,'http',reason='API_KEY_INVALID',retry_after=90)
                return 'OK'
        vault=VaultDouble();pool=KeyPool(vault,'prompt',Factory,output=lambda _:None)
        self.assertEqual(pool.generate(question),'OK');self.assertEqual([c[0] for c in calls],['one','two'])
        self.assertTrue(all(c[1] is question for c in calls))
        calls.clear();Factory.quota=True;vault=VaultDouble();pool=KeyPool(vault,'prompt',Factory,output=lambda _:None)
        with self.assertRaises(GeminiError):pool.generate(question)
        self.assertEqual([c[0] for c in calls],['one']);self.assertEqual(vault.wait,90)
    def test_worker_only_queues_plain_messages_from_active_sender_after_explicit_opt_in(self):
        from jat_design.agent_app import AgentWorker
        from jat_design.agent_store import key
        c=AgentControls();c.command('ON');c.command('AGENT ON')
        w=AgentWorker(Path('unused'),'bot','g','synthetic','prompt',c,output=lambda _:None)
        w.active_members={key('bot','g','A')}
        def e(sender):return {'event_name':'message.text.received','message':{'chat':{'id':'g','chat_type':'GROUP'},'from':{'id':sender,'is_bot':False},'text':'câu tiếp không @','message_id':'e','date':1}}
        self.assertFalse(w.submit(e('A'),c.snapshot(),0))
        c.command('FOLLOWUP ON XAC NHAN')
        self.assertTrue(w.submit(e('A'),c.snapshot(),0))
        self.assertFalse(w.submit(e('A'),c.snapshot(),0))
        self.assertFalse(w.submit(e('B'),c.snapshot(),0))
        status=w.status();self.assertGreater(status['observed']['plain'],0)
        self.assertNotIn('synthetic',str(status));self.assertFalse(status['reply_verified'])
    def test_worker_does_not_block_polling_and_off_cancels_model_work(self):
        from jat_design.agent_app import AgentWorker
        entered=threading.Event();release=threading.Event();sent=[]
        class BlockingPool(Pool):
            def generate(self,q):entered.set();release.wait(3);return 'answer'
        class SafeAPI:
            def __init__(self,*args):pass
            def typing(self,g):return True
            def sendMessage(self,g,text):sent.append(text);return {'message_id':'ack'}
        with tempfile.TemporaryDirectory() as temp,patch('jat_design.agent_store.protect',side_effect=double),\
             patch('jat_design.agent_app.Vault'),patch('jat_design.agent_app.KeyPool',return_value=BlockingPool()),\
             patch('jat_design.agent_app.AgentAPI',SafeAPI),patch('jat_design.agent_app.AgentTransport'):
            controls=AgentControls();controls.command('ON');controls.command('AGENT ON')
            worker=AgentWorker(Path(temp),'bot','g','synthetic','prompt',controls,output=lambda _:None)
            worker.thread.start()
            try:
                self.assertTrue(worker.ready.wait(2));self.assertFalse(worker.failed)
                def event(sender):return {'event_name':'message.text.received','message':{'chat':{'id':'g','chat_type':'GROUP'},'from':{'id':sender,'is_bot':False},'message_id':sender,'date':time.time()*1000,'text':TRIGGER+' question'}}
                self.assertTrue(worker.submit(event('A'),controls.snapshot(),time.monotonic()));self.assertTrue(entered.wait(2))
                poll_count=0
                for sender in ('B','C'):
                    # Caller/poller remains free while model is in worker thread.
                    poll_count+=1;self.assertTrue(worker.submit(event(sender),controls.snapshot(),time.monotonic()))
                self.assertEqual(poll_count,2);self.assertEqual(worker.status()['pending'],3)
                controls.command('OFF');release.set();controls.command('QUIT')
            finally:release.set();controls.command('QUIT');worker.thread.join(4)
            self.assertFalse(worker.thread.is_alive());self.assertEqual(sent,[])


@unittest.skipUnless(os.name=='nt','Native Windows DPAPI required')
class NativeAgentTests(unittest.TestCase):
    def test_real_dpapi_alias_history_roundtrip_and_ttl(self):
        with tempfile.TemporaryDirectory() as temp:
            clock=Clock();path=Path(temp)/'agent.db';s=AgentStore(path,clock.now)
            s.bind('synthetic-bot','synthetic-group','synthetic-member','AI JAT')
            version,_=s.touch('synthetic-bot','synthetic-group','synthetic-member')
            s.append('synthetic-bot','synthetic-group','synthetic-member',version,'synthetic-private-question','synthetic-private-answer');s.close()
            self.assertNotIn(b'synthetic-private-question',path.read_bytes())
            s=AgentStore(path,clock.now);self.assertEqual(s.alias('synthetic-bot','synthetic-group','synthetic-member'),'AI JAT')
            self.assertEqual(len(s.session('synthetic-bot','synthetic-group','synthetic-member')['history']),1)
            clock.advance(301);s.prune();self.assertIsNone(s.session('synthetic-bot','synthetic-group','synthetic-member'));s.close()
