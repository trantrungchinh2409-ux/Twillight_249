import copy
import tempfile
from pathlib import Path
import unittest
from jat_design.auto_reply import AutoResponder, Controls, TRIGGER, REPLY
from jat_design.state import State
from jat_design.official_api import APIError

NOW = 1800000000.0
EVENT = {'event_name': 'message.text.received', 'message': {
    'chat': {'id': 'allowed-group', 'chat_type': 'GROUP'},
    'from': {'id': 'human', 'is_bot': False}, 'message_id': 'one',
    'date': NOW*1000, 'text': TRIGGER+' xin chào'}}


class API:
    def __init__(self, fail=False): self.calls, self.fail = [], fail
    def sendMessage(self, group, text):
        self.calls.append((group, text))
        if self.fail: raise APIError('secret-url', kind='timeout')
        return {'message_id': 'dummy-ack'}


class AutoTests(unittest.TestCase):
    def setUp(self):
        self.state = State(':memory:')
        self.now = NOW
        self.engine = AutoResponder(self.state, 'bot', 'allowed-group', clock=lambda: self.now)
        self.api = API()
    def tearDown(self): self.state.close()
    def handle(self, e=None, on=True):
        return self.engine.handle(self.api, EVENT if e is None else e, on, NOW*1000-1000)

    def test_default_off_and_explicit_controls(self):
        c = Controls()
        self.assertFalse(c.snapshot()[0])
        c.command('ON'); self.assertTrue(c.snapshot()[0])
        c.command('OFF'); self.assertFalse(c.snapshot()[0])
        self.assertEqual(self.handle(on=False), 'off')
        self.assertEqual(self.api.calls, [])

    def test_exact_text_sends_exact_reply(self):
        self.assertEqual(self.handle(), 'sent')
        self.assertEqual(self.api.calls, [('allowed-group', 'JAT Design đã nhận tin!')])
        self.assertEqual(self.handle(), 'duplicate')
        self.assertEqual(len(self.api.calls), 1)

    def test_plain_reply_case_mismatch_private_and_bot_are_ignored(self):
        for variant in ('plain', 'reply', 'case', 'other_group', 'private', 'self', 'bot', 'missing_bot_flag'):
            e = copy.deepcopy(EVENT)
            if variant in ('plain', 'reply'): e['message']['text'] = 'xin chào'
            if variant == 'reply': e['message']['reply_to'] = {'from': {'id': 'bot'}}
            if variant == 'case': e['message']['text'] = '@bot JAT Design'
            if variant == 'other_group': e['message']['chat']['id'] = 'wrong-group'
            if variant == 'private': e['message']['chat']['chat_type'] = 'PRIVATE'
            if variant == 'self': e['message']['from']['id'] = 'bot'
            if variant == 'bot': e['message']['from']['is_bot'] = True
            if variant == 'missing_bot_flag': del e['message']['from']['is_bot']
            self.assertEqual(self.handle(e), 'ignored', variant)
        self.assertEqual(self.api.calls, [])

    def test_reply_containing_exact_text_is_allowed_as_requested(self):
        e = copy.deepcopy(EVENT); e['message']['reply_to'] = {'from': {'id': 'bot'}}
        self.assertEqual(self.handle(e), 'sent')

    def test_cooldown_consumes_event_so_it_is_not_sent_later(self):
        self.assertEqual(self.handle(), 'sent')
        e = copy.deepcopy(EVENT); e['message']['message_id'] = 'two'
        self.now += 9
        self.assertEqual(self.handle(e), 'cooldown')
        self.now += 2
        self.assertEqual(self.handle(e), 'duplicate')
        e['message']['message_id'] = 'three'
        self.assertEqual(self.handle(e), 'sent')

    def test_five_attempts_limit_survives_off_on(self):
        for index in range(5):
            e = copy.deepcopy(EVENT); e['message']['message_id'] = str(index)
            self.now = NOW + index*10
            self.assertEqual(self.handle(e), 'sent')
        self.assertEqual(self.handle(on=False), 'off')
        e['message']['message_id'] = 'six'
        self.assertEqual(self.handle(e), 'limit')
        self.assertEqual(len(self.api.calls), 5)

    def test_off_immediately_before_send_consumes_but_does_not_send(self):
        self.assertEqual(self.engine.handle(self.api, EVENT, True, NOW*1000-1000,
                         still_on=lambda: False), 'off')
        self.assertEqual(self.api.calls, [])

    def test_backlog_before_on_cannot_trigger(self):
        self.assertEqual(self.engine.handle(self.api, EVENT, True, NOW*1000+1), 'old_or_unknown_time')
        e = copy.deepcopy(EVENT); del e['message']['date']
        self.assertEqual(self.handle(e), 'old_or_unknown_time')

    def test_timeout_blocks_further_sends_even_new_event(self):
        self.api.fail = True
        self.assertEqual(self.handle(), 'uncertain_blocked')
        self.api.fail = False
        e = copy.deepcopy(EVENT); e['message']['message_id'] = 'new-event'
        self.now += 20
        self.assertEqual(self.handle(e), 'uncertain_blocked')
        self.assertEqual(len(self.api.calls), 1)
        self.assertEqual(self.engine.last_error, {'kind': 'timeout', 'code': None})

    def test_dedup_and_uncertain_guard_persist_through_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'auto.db'
            s = State(path)
            try:
                engine = AutoResponder(s, 'bot', 'allowed-group', clock=lambda: NOW)
                self.assertEqual(engine.handle(API(True), EVENT, True, NOW*1000-1), 'uncertain_blocked')
            finally: s.close()
            s = State(path)
            try:
                restarted = AutoResponder(s, 'bot', 'allowed-group', clock=lambda: NOW+20)
                self.assertTrue(restarted.blocked())
                e = copy.deepcopy(EVENT); e['message']['message_id'] = 'new'
                api = API()
                self.assertEqual(restarted.handle(api, e, True, NOW*1000-1), 'uncertain_blocked')
                self.assertEqual(api.calls, [])
            finally: s.close()
