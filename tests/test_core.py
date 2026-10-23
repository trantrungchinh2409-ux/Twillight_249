import contextlib
import io
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from jat_design.cli import main
from jat_design.core import DeliveryUncertain, Engine, Event, REPLY
from jat_design.mock_api import MockAPI
from jat_design.official_api import MentionContractNotVerified, parse_event
from jat_design.state import State


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.state = State(':memory:')
        self.addCleanup(self.state.close)
        self.engine = Engine('jat-id', self.state)
        self.event = Event('event-1', 'group-1', 'group', 'member-1', False,
                           ('jat-id',), 'Xin chào')

    def check_ignored(self, **changes):
        api = MockAPI([replace(self.event, **changes)])
        self.assertEqual(self.engine.step(api), 'ignored')
        self.assertEqual(api.sent, [])

    def test_group_id_mention_replies_fixed_text(self):
        api = MockAPI([self.event])
        self.assertEqual(self.engine.step(api), 'sent')
        self.assertEqual(api.sent, [('group-1', REPLY)])

    def test_private_even_with_mention_ignored(self):
        self.check_ignored(chat_kind='private')

    def test_display_name_text_is_not_a_mention(self):
        self.check_ignored(mentioned_ids=(), text='@Bot JAT Design')

    def test_other_bot_mention_ignored(self):
        self.check_ignored(mentioned_ids=('other-id',))

    def test_bot_sender_ignored(self):
        self.check_ignored(sender_is_bot=True)

    def test_self_sender_ignored(self):
        self.check_ignored(sender_id='jat-id')

    def test_unknown_chat_type_ignored(self):
        self.check_ignored(chat_kind='unknown')

    def test_empty_and_malformed_fields_ignored(self):
        for changes in ({'event_id': ''}, {'chat_id': ''}, {'sender_id': ''},
                        {'text': ''}, {'text': None}, {'mentioned_ids': None},
                        {'mentioned_ids': 'jat-id'}, {'sender_is_bot': None}):
            with self.subTest(changes=changes):
                self.check_ignored(**changes)

    def test_non_event_ignored(self):
        self.assertEqual(self.engine.step(MockAPI([{'message': 'unverified'}])), 'ignored')

    def test_duplicate_only_replies_once(self):
        api = MockAPI([self.event, self.event])
        self.assertEqual(self.engine.step(api), 'sent')
        self.assertEqual(self.engine.step(api), 'duplicate')
        self.assertEqual(len(api.sent), 1)

    def test_same_event_id_different_chat_is_independent(self):
        api = MockAPI([self.event, replace(self.event, chat_id='group-2')])
        self.assertEqual([self.engine.step(api), self.engine.step(api)], ['sent', 'sent'])

    def test_empty_poll(self):
        self.assertEqual(self.engine.step(MockAPI([])), 'idle')

    def test_persistent_duplicate_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'state.db'
            first = State(path)
            try:
                Engine('jat-id', first).step(MockAPI([self.event]))
            finally:
                first.close()
            second = State(path)
            try:
                api = MockAPI([self.event])
                self.assertEqual(Engine('jat-id', second).step(api), 'duplicate')
                self.assertEqual(api.sent, [])
            finally:
                second.close()

    def test_send_failure_is_uncertain_and_not_retried(self):
        class FailingAPI(MockAPI):
            def sendMessage(self, chat_id, text):
                raise RuntimeError('secret-token-must-not-escape')
        api = FailingAPI([self.event, self.event])
        with self.assertRaises(DeliveryUncertain) as result:
            self.engine.step(api)
        self.assertNotIn('secret-token', str(result.exception))
        self.assertTrue(result.exception.__suppress_context__)
        self.assertEqual(self.engine.step(api), 'duplicate')
        status = self.state.db.execute('SELECT status FROM deliveries').fetchone()[0]
        self.assertEqual(status, 'uncertain')

    def test_poll_failure_never_sends(self):
        class FailingPoll(MockAPI):
            def getUpdates(self):
                raise TimeoutError('poll failed')
        api = FailingPoll([])
        with self.assertRaises(TimeoutError):
            self.engine.step(api)
        self.assertEqual(api.sent, [])

    def test_blank_bot_id_rejected(self):
        for bot_id in ('', ' ', None):
            with self.assertRaises(ValueError):
                Engine(bot_id, self.state)

    def test_official_adapter_fails_closed(self):
        with self.assertRaises(MentionContractNotVerified):
            parse_event({'event_name': 'message.text.received',
                         'message': {'chat': {'chat_type': 'GROUP'}, 'from': {}}})

    def test_live_exit_status_is_blocked(self):
        with contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(main(['--live']), 2)
        self.assertIn('LIVE BLOCKED', output.getvalue())

    def test_packaged_self_test(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['--self-test']), 0)
        self.assertIn('internal mock only', output.getvalue())


if __name__ == '__main__':
    unittest.main()
