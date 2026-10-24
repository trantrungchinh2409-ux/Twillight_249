"""Synthetic send transport; no real Zalo send in tests."""
import copy
import tempfile
from pathlib import Path
import unittest
from jat_design.send_once import APPROVAL, REPLY, digest, eligible, send_once
from jat_design.state import State

MARKER = 'JAT-0123456789ABCDEF'
EVENT = {'event_name': 'message.text.received', 'message': {
    'message_id': 'synthetic-event', 'chat': {'id': 'synthetic-group', 'chat_type': 'GROUP'},
    'from': {'id': 'synthetic-human', 'is_bot': False}, 'text': '@bot '+MARKER}}


class API:
    def __init__(self, fail=False):
        self.sent, self.fail = [], fail
    def sendMessage(self, chat_id, text):
        self.sent.append((chat_id, text))
        if self.fail:
            raise TimeoutError('do not expose details')
        return {'message_id': 'synthetic-ack'}


class OnceTests(unittest.TestCase):
    def test_preflight_two_successes_no_send(self):
        from test_polling_test import Fake
        from jat_design.send_once import preflight
        api, statuses = Fake({}, EVENT), []
        self.assertTrue(preflight(api, statuses.append, output=lambda _: None))
        self.assertEqual(api.calls, [('getUpdates', {'timeout': '30'}, 40)]*2)
        self.assertEqual(statuses[-1], {'phase': 'preflight_passed', 'check': 2})

    def test_preflight_stops_first_error_with_actual_safe_code(self):
        from test_polling_test import Fake
        from jat_design.send_once import preflight
        from jat_design.official_api import APIError
        api, statuses = Fake(APIError('private-url', 429, 'api'), EVENT), []
        self.assertFalse(preflight(api, statuses.append, output=lambda _: None))
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(statuses[-1], {'phase': 'preflight_failed', 'kind': 'api', 'code': 429})

    def test_one_session_receive_does_not_retry_network_error(self):
        from test_polling_test import Fake
        from jat_design.polling_test import receive_one
        from jat_design.official_api import APIError
        api = Fake(APIError('hidden', kind='network'), EVENT)
        waits = []
        self.assertIsNone(receive_one(api, wait=waits.append, output=lambda _: None, stop_on_error=True))
        self.assertEqual(waits, [])
        self.assertEqual(len(api.calls), 1)

    def test_exact_reply_single_global_attempt_even_new_event(self):
        state, api = State(':memory:'), API()
        try:
            self.assertEqual(send_once(api, state, 'bot', EVENT, MARKER), 'api_acknowledged')
            other = copy.deepcopy(EVENT)
            other['message']['message_id'] = 'new-event'
            self.assertEqual(send_once(api, state, 'bot', other, MARKER), 'already_attempted')
            self.assertEqual(api.sent, [('synthetic-group', 'JAT Design đã hoạt động thành công!')])
        finally:
            state.close()

    def test_reopen_db_after_timeout_never_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            path, api = Path(directory)/'once.db', API(True)
            state = State(path)
            try:
                self.assertEqual(send_once(api, state, 'bot', EVENT, MARKER), 'uncertain')
            finally:
                state.close()
            state = State(path)
            try:
                self.assertEqual(send_once(api, state, 'bot', EVENT, MARKER), 'already_attempted')
                self.assertEqual(len(api.sent), 1)
            finally:
                state.close()

    def test_reject_private_self_bot_missing_sender_and_wrong_marker(self):
        variants = []
        for change in ('private', 'self', 'bot', 'unknown_sender', 'wrong_marker', 'prefix_only'):
            e = copy.deepcopy(EVENT)
            if change == 'private': e['message']['chat']['chat_type'] = 'PRIVATE'
            if change == 'self': e['message']['from']['id'] = 'bot'
            if change == 'bot': e['message']['from']['is_bot'] = True
            if change == 'unknown_sender': del e['message']['from']['is_bot']
            if change == 'wrong_marker': e['message']['text'] = '@bot another test'
            if change == 'prefix_only': e['message']['text'] = MARKER+'suffix'
            variants.append(e)
        state, api = State(':memory:'), API()
        try:
            for event in variants:
                self.assertFalse(eligible(event, 'bot', MARKER))
                self.assertEqual(send_once(api, state, 'bot', event, MARKER), 'ignored')
            self.assertEqual(api.sent, [])
        finally:
            state.close()

    def test_reservation_is_committed_before_send(self):
        state = State(':memory:')
        case = self
        class Checking(API):
            def sendMessage(self, chat_id, text):
                row = state.db.execute('SELECT status FROM deliveries WHERE chat_id=? AND event_id=?',
                                       (digest('bot'), APPROVAL)).fetchone()
                case.assertEqual(row, ('reserved',))
                return super().sendMessage(chat_id, text)
        try:
            self.assertEqual(send_once(Checking(), state, 'bot', EVENT, MARKER), 'api_acknowledged')
        finally:
            state.close()

    def test_waiting_skips_unrelated_event(self):
        from test_polling_test import Fake
        from jat_design.polling_test import receive_one
        unrelated = copy.deepcopy(EVENT)
        unrelated['message']['text'] = 'not the marker'
        api = Fake(unrelated, EVENT)
        self.assertEqual(receive_one(api, wait=lambda _: None, output=lambda _: None,
                         accept=lambda e: eligible(e, 'bot', MARKER)), EVENT)
        self.assertEqual([c[0] for c in api.calls], ['getUpdates', 'getUpdates'])
