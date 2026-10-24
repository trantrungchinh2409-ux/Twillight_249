"""Synthetic receive-only cases; these are not captured Zalo events."""
import contextlib
import io
import json
import os
import unittest
from unittest.mock import patch
from jat_design import polling_test as p
from jat_design.official_api import APIError, ProtocolError

EVENT = {'event_name': 'message.text.received', 'message': {
    'message_id': 'synthetic-message', 'chat': {'id': 'private-group-id', 'chat_type': 'GROUP'},
    'from': {'id': 'private-member-id', 'display_name': 'private-name', 'is_bot': False},
    'text': 'private text and token', 'mentions': [{'user_id': 'bot-id'}],
    'reply_to': {'id': 'private-quote-id'}, 'untrusted-secret-key': 'secret-value'}}


class Fake:
    def __init__(self, *results):
        self.results, self.calls = list(results), []

    def post(self, method, payload, timeout):
        self.calls.append((method, payload, timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class PollingTests(unittest.TestCase):
    def test_poll_error_status_is_not_misreported_as_empty(self):
        api = Fake(APIError('secret-url', 429, 'api'), EVENT)
        logs, statuses = [], []
        self.assertEqual(p.receive_one(api, wait=lambda _: None, output=logs.append,
                                     on_status=statuses.append), EVENT)
        self.assertEqual(statuses[0], {'phase': 'poll_error', 'kind': 'api', 'code': 429})
        self.assertNotIn('secret-url', str(logs)+str(statuses))
        self.assertNotIn('Chưa có dữ liệu', str(logs))

    def test_filter_rejection_is_visible_and_does_not_send(self):
        api = Fake(EVENT, EVENT)
        statuses, logs = [], []
        calls = iter([False, True])
        self.assertEqual(p.receive_one(api, wait=lambda _: None, output=logs.append,
                                     accept=lambda _: next(calls), on_status=statuses.append), EVENT)
        self.assertEqual(statuses, [{'phase': 'event_rejected_by_send_filter'},
                                    {'phase': 'event_accepted'}])
        self.assertTrue(logs)
        self.assertEqual([c[0] for c in api.calls], ['getUpdates', 'getUpdates'])

    def test_interaction_metadata_is_not_destroyed(self):
        redactor = p.Redactor('bot-id')
        cleaned = redactor.clean({'message_type': 'MENTION', 'text': 'private content'})
        self.assertEqual(cleaned['message_type'], 'MENTION')
        self.assertEqual(cleaned['text'], '<string>')
        first = redactor.clean({'message_type': 'some-unverified-value'})
        second = p.Redactor('bot-id').clean({'message_type': 'some-unverified-value'})
        self.assertEqual(first, second)
        self.assertNotIn('some-unverified-value', str(first))
        extra = redactor.clean({'message': {'actual_field': 'private-value', 'text': 'secret'}})
        self.assertIn('actual_field', extra['message'])
        self.assertNotIn('private-value', str(extra))

    def test_webhook_blocks_poll_and_mutation_in_main(self):
        fake = Fake({'id': 'bot-id'}, {'url': 'https://private-webhook.example'})
        output = io.StringIO()
        with patch.object(p.sys.stdin, 'isatty', return_value=True), \
             patch.object(p.getpass, 'getpass', return_value='synthetic-not-a-token'), \
             patch.object(p, 'Transport', return_value=fake), \
             contextlib.redirect_stdout(output):
            self.assertEqual(p.main(), 3)
        self.assertEqual([c[0] for c in fake.calls], ['getMe', 'getWebhookInfo'])
        self.assertNotIn('private-webhook', output.getvalue())

    def test_unknown_webhook_state_fails_closed(self):
        for state in ({}, {'url': None}, [], {'url': False}):
            with self.assertRaises(ProtocolError):
                p.webhook_enabled(Fake(state))

    def test_empty_webhook_url_allows_observation(self):
        self.assertFalse(p.webhook_enabled(Fake({'url': ''})))

    def test_receive_real_shape_without_using_group_parser(self):
        fake = Fake(EVENT)
        self.assertEqual(p.receive_one(fake), EVENT)
        self.assertEqual(fake.calls, [('getUpdates', {'timeout': '30'}, 40)])

    def test_read_only_wrapper_rejects_all_writes(self):
        fake = Fake()
        for method in ('sendMessage', 'deleteWebhook', 'setWebhook', 'testWebhook'):
            with self.assertRaises(ValueError):
                p.ReadOnlyTransport(fake).post(method, {}, 15)
        self.assertEqual(fake.calls, [])

    def test_auth_failure_does_not_retry_or_print_details(self):
        fake = Fake(APIError('sensitive-detail', 401))
        output = []
        self.assertIsNone(p.receive_one(fake, output=output.append))
        self.assertEqual(len(fake.calls), 1)
        self.assertNotIn('sensitive-detail', str(output))

    def test_transient_failures_are_bounded(self):
        fake = Fake(*[APIError('private') for _ in range(3)])
        waits = []
        self.assertIsNone(p.receive_one(fake, wait=waits.append, output=lambda _: None))
        self.assertEqual(waits, [2, 4])
        self.assertEqual(len(fake.calls), 3)

    def test_quota_failure_waits_before_retry(self):
        fake = Fake(APIError('private', 429), EVENT)
        waits = []
        self.assertEqual(p.receive_one(fake, wait=waits.append, output=lambda _: None), EVENT)
        self.assertEqual(waits, [30])

    def test_unexpected_payload_never_counts_as_received(self):
        for result in ([], {'event_name': {}}, {'event_name': 'unknown'},
                       {'event_name': 'message.text.received', 'message': {}}):
            self.assertIsNone(p.receive_one(Fake(result), output=lambda _: None))

    def test_private_is_valid_but_not_group(self):
        event = json.loads(json.dumps(EVENT))
        event['message']['chat']['chat_type'] = 'PRIVATE'
        self.assertTrue(p.valid_event(event))
        self.assertNotEqual(event['message']['chat']['chat_type'], 'GROUP')

    def test_schema_removes_content_and_preserves_bot_identity_relation(self):
        cleaned = p.Redactor('bot-id').clean(EVENT)
        serialized = json.dumps(cleaned)
        for secret in ('private-', 'private text', 'secret-value', 'untrusted-secret-key'):
            self.assertNotIn(secret, serialized)
        self.assertEqual(cleaned['message']['mentions'][0]['user_id'], '<bot_id>')
        self.assertNotIn('mention_verified', cleaned)

    @unittest.skipUnless(os.name == 'nt', 'Native Windows mutex')
    def test_mutex_rejects_second_copy_and_releases(self):
        with p.TokenLock('synthetic-lock-token'):
            with self.assertRaises(RuntimeError):
                with p.TokenLock('synthetic-lock-token'):
                    self.fail('Second copy acquired lock')
        with p.TokenLock('synthetic-lock-token'):
            pass

    def test_no_token_echo_on_redirected_stdin(self):
        with patch.object(p.sys.stdin, 'isatty', return_value=False), \
             patch.object(p.getpass, 'getpass') as prompt, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(p.main(), 2)
            prompt.assert_not_called()
