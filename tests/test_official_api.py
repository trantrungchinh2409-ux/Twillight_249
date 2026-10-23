import contextlib
import copy
import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from jat_design.cli import main
from jat_design.official_api import (
    APIError, MentionContractNotVerified, NoRedirect, OfficialAPI,
    ProtocolError, Transport, parse_event)

# Transcribed from the official webhook sample, with dummy IDs and text.
# Group variants below are synthetic negative cases, not captured group events.
PRIVATE = {'event_name': 'message.text.received', 'message': {
    'from': {'id': 'member', 'display_name': 'Dummy', 'is_bot': False},
    'chat': {'id': 'member', 'chat_type': 'PRIVATE'},
    'text': 'Hello', 'message_id': 'message-1', 'date': 1750316131602}}


class Response:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, limit):
        return self.data[:limit]


class Opener:
    def __init__(self, body):
        self.body = body
        self.calls = []
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        return Response(json.dumps(self.body).encode())


class OfficialTests(unittest.TestCase):
    def api(self, result):
        self.opener = Opener({'ok': True, 'result': result})
        return OfficialAPI(Transport('dummy/not-a-real-token', self.opener))

    def test_get_me_post_and_url(self):
        self.assertEqual(self.api({'id': 'bot-id'}).getMe(), 'bot-id')
        request, timeout = self.opener.calls[0]
        self.assertEqual(request.full_url,
                         'https://bot-api.zaloplatforms.com/botdummy%2Fnot-a-real-token/getMe')
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(json.loads(request.data), {})
        self.assertEqual(timeout, 15)

    def test_poll_documented_single_object_not_telegram_batch(self):
        event = self.api(PRIVATE).getUpdates()
        self.assertEqual(event.chat_kind, 'private')
        self.assertEqual(event.mentioned_ids, ())
        request, timeout = self.opener.calls[0]
        self.assertEqual(json.loads(request.data), {'timeout': '30'})
        self.assertGreater(timeout, 30)
        self.assertNotIn('offset', json.loads(request.data))

    def test_send_exact_documented_body_and_ack(self):
        self.api({'message_id': 'sent-1', 'date': 1749632637199}).sendMessage('group-1', 'Hello')
        request, timeout = self.opener.calls[0]
        self.assertTrue(request.full_url.endswith('/sendMessage'))
        self.assertEqual(json.loads(request.data), {'chat_id': 'group-1', 'text': 'Hello'})

    def test_send_rejects_bad_parameters_before_network(self):
        api = self.api({'message_id': 'sent-1'})
        for chat_id, text in [('', 'hi'), ('group', ''), ('group', 'a' * 2001)]:
            with self.assertRaises(ValueError):
                api.sendMessage(chat_id, text)
        self.assertEqual(self.opener.calls, [])

    def test_send_without_ack_fails(self):
        with self.assertRaises(ProtocolError):
            self.api({}).sendMessage('group', 'hello')

    def test_api_error_description_is_not_exposed(self):
        opener = Opener({'ok': False, 'description': 'sensitive-token-and-user-text'})
        with self.assertRaises(APIError) as result:
            Transport('dummy-token', opener).post('getMe', {}, 15)
        self.assertNotIn('sensitive', str(result.exception))

    def test_transport_error_url_is_hidden(self):
        class Failing(Opener):
            def open(self, request, timeout):
                raise urllib.error.URLError(request.full_url)
        with self.assertRaises(APIError) as result:
            Transport('dummy-secret', Failing({})).post('getMe', {}, 15)
        self.assertNotIn('dummy-secret', str(result.exception))
        self.assertTrue(result.exception.__suppress_context__)

    def test_invalid_json_is_sanitized(self):
        class Invalid(Opener):
            def open(self, request, timeout):
                return Response(b'not json dummy-secret')
        with self.assertRaises(APIError) as result:
            Transport('dummy-secret', Invalid({})).post('getMe', {}, 15)
        self.assertNotIn('dummy-secret', str(result.exception))

    def test_batch_result_not_assumed(self):
        with self.assertRaises(ProtocolError):
            Transport('dummy', Opener({'ok': True, 'result': []})).post('getUpdates', {}, 40)

    def test_unverified_group_even_with_mentions_fails_closed(self):
        event = copy.deepcopy(PRIVATE)
        event['message']['chat']['chat_type'] = 'GROUP'
        event['message']['mentions'] = [{'id': 'bot-id'}]  # deliberately UNVERIFIED
        with self.assertRaises(MentionContractNotVerified):
            parse_event(event)

    def test_non_text_is_not_replied_to(self):
        self.assertIsNone(parse_event({'event_name': 'message.image.received'}))

    def test_unknown_event_rejected(self):
        with self.assertRaises(ProtocolError):
            parse_event({'event_name': 'invented.event'})

    def test_missing_sender_bot_flag_rejected(self):
        event = copy.deepcopy(PRIVATE)
        del event['message']['from']['is_bot']
        with self.assertRaises(ProtocolError):
            parse_event(event)

    def test_redirect_refused(self):
        with self.assertRaises(APIError):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example/')

    def test_method_allowlist(self):
        with self.assertRaises(ValueError):
            Transport('dummy', Opener({})).post('invented', {}, 15)

    def test_no_automatic_network_retry(self):
        class Failing(Opener):
            def open(self, request, timeout):
                self.calls.append(request)
                raise TimeoutError('send may already be delivered')
        opener = Failing({})
        with self.assertRaises(APIError):
            OfficialAPI(Transport('dummy', opener)).sendMessage('group', 'Hello')
        self.assertEqual(len(opener.calls), 1)

    @patch.dict('os.environ', {'ZALO_BOT_TOKEN': 'dummy-secret'})
    @patch('jat_design.cli.OfficialAPI')
    def test_check_api_only_calls_identity(self, api_class):
        api_class.return_value.getMe.return_value = 'bot-id'
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['--check-api']), 0)
        api_class.return_value.getMe.assert_called_once_with()
        api_class.return_value.getUpdates.assert_not_called()
        api_class.return_value.sendMessage.assert_not_called()
        self.assertNotIn('dummy-secret', output.getvalue())
