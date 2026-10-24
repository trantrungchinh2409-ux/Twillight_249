import copy
from pathlib import Path
import tempfile
import unittest
from jat_design.state import State
from jat_design.managed_limits import ManagedResponder, NOTICE
from jat_design.gemini_client import GeminiError
from jat_design.managed_ai import status_text

NOW = 1800000000.0


class Pool:
    def __init__(self): self.calls, self.failure, self.wait = 0, None, 0
    def wait_remaining(self): return self.wait
    def generate(self, question):
        self.calls += 1
        if self.failure: raise self.failure
        return 'Đáp án ngắn.'


class API:
    def __init__(self): self.calls, self.failure = [], False
    def sendMessage(self, group, text):
        self.calls.append((group, text))
        if self.failure: raise TimeoutError('private-key-text')
        return {'message_id': 'synthetic-ack'}


class LimitTests(unittest.TestCase):
    def setUp(self):
        self.state = State(':memory:'); self.now = NOW
        self.engine = ManagedResponder(self.state, 'bot', 'group', clock=lambda: self.now)
        self.pool, self.api = Pool(), API()
    def tearDown(self): self.state.close()
    def event(self, number):
        return {'event_name': 'message.text.received', 'message': {
            'chat': {'id': 'group', 'chat_type': 'GROUP'}, 'from': {'id': 'human', 'is_bot': False},
            'message_id': str(number), 'text': '@Bot JAT Design question', 'date': self.now*1000}}
    def handle(self, number, event=None, on=True, still_on=lambda: True):
        return self.engine.handle(self.api, self.pool, self.event(number) if event is None else event,
                                  on, NOW*1000-1, still_on=still_on)
    def fill(self):
        for i in range(10):
            self.now = NOW+i*10
            self.assertEqual(self.handle(i), 'sent')

    def test_ten_calls_one_notice_no_more_gemini_then_resume(self):
        self.fill()
        self.assertEqual(self.pool.calls, 10)
        self.assertEqual(self.engine.status()['remaining'], 0)
        self.now = NOW+100
        self.assertEqual(self.handle('notice'), 'notice_sent')
        self.assertEqual(self.api.calls[-1], ('group', NOTICE))
        for i in range(5):
            self.now += 10
            self.assertEqual(self.handle('paused'+str(i)), 'internal_wait')
        self.assertEqual(self.pool.calls, 10)
        self.assertEqual(sum(text == NOTICE for _, text in self.api.calls), 1)
        self.now = NOW+390
        self.assertEqual(self.handle('resumed'), 'sent')
        self.assertEqual(self.pool.calls, 11)

    def test_sliding_window_does_not_pause_if_calls_aged_out(self):
        for i in range(15):
            self.now = NOW+i*20
            self.assertEqual(self.handle(i), 'sent')
        self.assertEqual(self.engine.status()['local_until'], 0)
        self.assertEqual(self.pool.calls, 15)

    def test_dedup_cooldown_and_off(self):
        e = self.event('one')
        self.assertEqual(self.handle('one', on=False), 'off')
        self.assertEqual(self.handle('one', e), 'sent')
        self.assertEqual(self.handle('one', e), 'duplicate')
        self.now += 9
        self.assertEqual(self.handle('cooldown'), 'cooldown')
        self.now += 1
        self.assertEqual(self.handle('cooldown'), 'duplicate')
        self.assertEqual(self.handle('off-during-send', still_on=lambda: False), 'off')
        self.assertEqual(self.pool.calls, 1)

    def test_private_other_group_self_bot_plain_text_rejected(self):
        for variant in ('private', 'other', 'self', 'bot', 'plain', 'unknown_sender'):
            e = self.event(variant)
            if variant == 'private': e['message']['chat']['chat_type'] = 'PRIVATE'
            if variant == 'other': e['message']['chat']['id'] = 'different'
            if variant == 'self': e['message']['from']['id'] = 'bot'
            if variant == 'bot': e['message']['from']['is_bot'] = True
            if variant == 'plain': e['message']['text'] = 'reply without trigger'
            if variant == 'unknown_sender': del e['message']['from']['is_bot']
            self.assertEqual(self.handle(variant, e), 'ignored')
        self.assertEqual(self.pool.calls, 0)
        self.assertEqual(self.api.calls, [])

    def test_google_429_wait_is_separate_no_internal_notice(self):
        self.pool.failure = GeminiError('private', 429, 'http', retry_after=75)
        self.assertEqual(self.handle('quota'), 'google_wait')
        self.now += 11
        self.pool.failure = None
        self.assertEqual(self.handle('waiting'), 'google_wait')
        self.assertEqual(self.pool.calls, 1)
        self.assertEqual(self.api.calls, [])
        self.now = NOW+75
        self.assertEqual(self.handle('after-wait'), 'sent')

    def test_zalo_timeout_blocks_future_new_event_no_retry(self):
        self.api.failure = True
        self.assertEqual(self.handle('timeout'), 'uncertain_blocked')
        self.now += 30; self.api.failure = False
        self.assertEqual(self.handle('new'), 'uncertain_blocked')
        self.assertEqual(self.pool.calls, 1)
        self.assertEqual(len(self.api.calls), 1)

    def test_notice_timeout_is_reserved_once_and_stops(self):
        self.fill(); self.now += 10; self.api.failure = True
        self.assertEqual(self.handle('notice'), 'uncertain_blocked')
        self.assertTrue(self.engine.status()['notice_reserved'])
        self.now += 20
        self.assertEqual(self.handle('later'), 'uncertain_blocked')
        self.assertEqual(sum(text == NOTICE for _, text in self.api.calls), 1)
        self.assertEqual(self.pool.calls, 10)

    def test_restart_preserves_pause_notice_and_google_wait(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'limits.db'
            s = State(path)
            try:
                engine = ManagedResponder(s, 'bot', 'group', clock=lambda: self.now)
                for i in range(10):
                    self.now = NOW+i*10
                    self.assertEqual(engine.handle(self.api, self.pool, self.event(i), True, NOW*1000-1), 'sent')
                self.now += 10
                self.assertEqual(engine.handle(self.api, self.pool, self.event('notice'), True, NOW*1000-1), 'notice_sent')
            finally: s.close()
            s = State(path)
            try:
                reopened = ManagedResponder(s, 'bot', 'group', clock=lambda: self.now)
                self.assertEqual(reopened.status()['remaining'], 0)
                self.assertTrue(reopened.status()['notice_reserved'])
                self.now += 11
                self.assertEqual(reopened.handle(self.api, self.pool, self.event('restart'), True, NOW*1000-1), 'internal_wait')
                self.assertEqual(self.pool.calls, 10)
            finally: s.close()

    def test_status_calculates_wait_without_db_thread_access(self):
        self.fill()
        result = status_text(self.engine.status(), NOW+500, now=self.now)
        self.assertIn('còn 0/10', result)
        self.assertIn('300s', result)
        self.assertIn('410s', result)

    def test_google_wait_and_uncertain_guard_survive_restart(self):
        for uncertain in (False, True):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder)/'restart.db'
                s = State(path)
                engine = ManagedResponder(s, 'bot', 'group', clock=lambda: self.now)
                pool, api = Pool(), API()
                if uncertain: api.failure = True
                else: pool.failure = GeminiError('safe', 429, 'http', retry_after=80)
                expected = 'uncertain_blocked' if uncertain else 'google_wait'
                try:
                    self.assertEqual(engine.handle(api, pool, self.event('first'), True, NOW*1000-1), expected)
                finally: s.close()
                s = State(path)
                try:
                    reopened = ManagedResponder(s, 'bot', 'group', clock=lambda: self.now)
                    self.now += 11
                    pool.failure = None; api.failure = False
                    self.assertEqual(reopened.handle(api, pool, self.event('after-restart'), True, NOW*1000-1), expected)
                    self.assertEqual(pool.calls, 1)
                    self.assertEqual(len(api.calls), 1 if uncertain else 0)
                finally: s.close()

    def test_new_key_pool_does_not_reset_shared_budget(self):
        self.fill()
        replacement_pool = Pool()
        self.now += 10
        self.assertEqual(self.engine.handle(self.api, replacement_pool, self.event('different-key'),
                                          True, NOW*1000-1), 'notice_sent')
        self.assertEqual(replacement_pool.calls, 0)
        self.assertEqual(self.engine.status()['remaining'], 0)
