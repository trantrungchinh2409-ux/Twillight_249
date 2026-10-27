"""Reproduce long-poll toggle loss without real Zalo traffic or credentials."""
import unittest
from unittest.mock import Mock
from jat_design.agent_engine import AgentControls


class DispatchRaceTests(unittest.TestCase):
    def setUp(self):
        self.time=[1000.0];self.c=AgentControls(lambda:self.time[0]);self.c.command('ON');self.c.command('AGENT ON')
        self.worker=Mock();self.worker.submit.return_value=True
    def e(self,stamp):return {'event_name':'message.text.received','message':{'date':stamp}}
    def test_reproduces_original_drop_after_followup_enabled_during_long_poll(self):
        pending=self.c.snapshot();self.time[0]=1001;self.c.command('FOLLOWUP ON XAC NHAN')
        self.assertFalse(self.c.valid(pending))
        # Original app uses pending snapshot here, so even a fresh1001.5s event is discarded.
        if self.c.valid(pending):self.worker.submit(self.e(1001500),pending,1.5)
        self.worker.submit.assert_not_called()

    def test_fresh_event_after_followup_toggle_uses_current_snapshot(self):
        from jat_design.agent_app import dispatch_received_event
        self.time[0]=1001;self.c.command('FOLLOWUP ON XAC NHAN')
        self.time[0]=1002
        self.assertTrue(dispatch_received_event(self.c,self.worker,self.e(1001500),2,lambda:self.time[0]))
        self.assertTrue(self.worker.submit.call_args[0][1]['catchall'])
    def test_off_and_off_on_still_reject_events_before_new_arm_boundary(self):
        from jat_design.agent_app import dispatch_received_event
        self.c.command('OFF')
        self.assertFalse(dispatch_received_event(self.c,self.worker,self.e(1001500),2,lambda:1002))
        self.time[0]=1003;self.c.command('ON')
        self.assertFalse(dispatch_received_event(self.c,self.worker,self.e(1001500),4,lambda:1004))
        self.worker.submit.assert_not_called()
    def test_malformed_future_nan_events_still_fail_closed(self):
        from jat_design.agent_app import dispatch_received_event
        for e in (None,{},self.e(None),self.e(True),self.e(float('nan')),self.e(2000000)):
            self.assertFalse(dispatch_received_event(self.c,self.worker,e,1,lambda:1000))
        self.worker.submit.assert_not_called()


class ProbeMetadataTests(unittest.TestCase):
    def event(self,**changes):
        result={'event_name':'message.text.received','message':{'chat':{'id':'private-group','chat_type':'GROUP'},
               'from':{'id':'private-sender','is_bot':False},'text':'private-conversation','message_id':'private-event','date':1700000000000}}
        result['message'].update(changes);return result
    def test_plain_event_counted_before_worker_session_or_queue_rejection(self):
        from jat_design.agent_followup_probe import metadata
        r=metadata(self.event(),'bot','private-group','private-sender',set(),1700000001)
        self.assertTrue(r['plain_by_app_rule']);self.assertTrue(r['shared_valid_event'])
        self.assertTrue(r['worker_prefilter_pass']);self.assertFalse(r['dry_worker_would_queue'])
    def test_missing_sender_field_can_hide_event_from_existing_observed_plain(self):
        from jat_design.agent_followup_probe import metadata
        e=self.event();del e['message']['from']['is_bot']
        r=metadata(e,'bot','private-group',None,set(),1700000001)
        self.assertTrue(r['shared_valid_event']);self.assertTrue(r['plain_by_app_rule'])
        self.assertFalse(r['worker_prefilter_pass'])
    def test_unknown_contract_is_observed_before_shared_helper_silently_discards(self):
        from jat_design.agent_followup_probe import metadata
        e=self.event(message_id='');r=metadata(e,'bot','private-group',None,set(),1700000001)
        self.assertFalse(r['shared_valid_event']);self.assertTrue(r['plain_by_app_rule'])
    def test_trigger_inside_api_text_is_not_plain_even_when_tester_did_not_type_at(self):
        from jat_design.agent_followup_probe import metadata
        from jat_design.auto_reply import TRIGGER
        r=metadata(self.event(text='quoted '+TRIGGER+' text'),'bot','private-group',None,set(),1700000001)
        self.assertTrue(r['trigger_in_text']);self.assertFalse(r['plain_by_app_rule'])
    def test_private_values_never_appear_in_report_even_unknown_enum_values(self):
        import json
        from jat_design.agent_followup_probe import metadata
        e=self.event();e['event_name']='PRIVATE-TOKEN-UNKNOWN';e['message']['chat']['chat_type']='PRIVATE-NAME'
        r=metadata(e,'bot','private-group','private-sender',set(),1700000001);text=json.dumps(r)
        for secret in ('PRIVATE-TOKEN-UNKNOWN','PRIVATE-NAME','private-group','private-sender','private-event','private-conversation'):
            self.assertNotIn(secret,text)
        self.assertEqual(r['event'],'OTHER');self.assertEqual(r['chat'],'OTHER')
    def test_probe_never_starts_worker_or_sends_even_with_qualifying_active_sender(self):
        from unittest.mock import patch
        from jat_design.agent_store import key
        from jat_design.agent_followup_probe import metadata
        with patch('threading.Thread.start',side_effect=AssertionError('must not start')):
            r=metadata(self.event(),'bot','private-group','private-sender',{key('bot','private-group','private-sender')},1700000001)
        self.assertTrue(r['dry_worker_would_queue'])
    def test_raw_phase_distinguishes_api_empty_from_received_rejected_contract(self):
        from jat_design.agent_followup_probe import phase
        from test_agent_win7 import Clock
        clock=Clock()
        class Empty:
            def post(self,*args,**kwargs):return {}
        empty,_=phase(Empty(),'B','bot','private-group','private-sender','nonce',set(),output=lambda _:None,
                      clock=clock.monotonic,wait=clock.sleep,seconds=2)
        self.assertEqual(empty['nonempty'],0);self.assertGreater(empty['empty'],0)
        class Raw:
            def post(api,method,payload,timeout):
                self.assertEqual(method,'getUpdates');return self.event(message_id='',text='probe-nonce')
        received,_=phase(Raw(),'C','bot','private-group','private-sender','probe-nonce',set(),output=lambda _:None,
                         clock=clock.monotonic,wait=clock.sleep,seconds=2)
        self.assertEqual(received['status'],'RAW_MATCH_RECEIVED')
        self.assertFalse(received['events'][0]['shared_valid_event'])
    def test_existing_agent_sessions_read_only_and_only_return_internal_keys(self):
        import sqlite3,tempfile
        from pathlib import Path
        from unittest.mock import patch
        from jat_design.agent_followup_probe import active_keys_readonly
        from jat_design.agent_store import key
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);p=root/'agent_state.db'
            with sqlite3.connect(p) as db:
                db.execute('CREATE TABLE agent_sessions(k TEXT,g TEXT,expires REAL)')
                db.execute('INSERT INTO agent_sessions VALUES (?,?,?)',(key('b','g','u'),key('b','g'),2000))
            before=p.read_bytes()
            with patch('time.time',return_value=1000):r=active_keys_readonly(root,'b','g')
            self.assertEqual(r,{key('b','g','u')});self.assertEqual(p.read_bytes(),before)
