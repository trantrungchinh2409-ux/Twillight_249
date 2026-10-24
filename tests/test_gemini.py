import json
import unittest
import urllib.error
from jat_design.gemini_client import Gemini, GeminiError, compact, PREFERRED
from jat_design.ai_reply import AIForwarder
from test_official_api import Opener, Response


class Sequence:
    def __init__(self, *responses): self.responses, self.calls = list(responses), []
    def open(self, request, timeout):
        self.calls.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception): raise response
        return Response(json.dumps(response).encode())


ANSWER = {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'Xin chào. Tôi có thể hỗ trợ bạn.'}]}}]}


class GeminiTests(unittest.TestCase):
    def test_trial_budget_survives_recreating_controller(self):
        from jat_design.ai_reply import TrialQuota
        from jat_design.state import State
        state = State(':memory:')
        try:
            quota = TrialQuota(state, 'dummy-bot')
            self.assertEqual(quota.used(), 0)
            for _ in range(3): self.assertTrue(quota.claim())
            reopened = TrialQuota(state, 'dummy-bot')
            self.assertEqual(reopened.used(), 3)
            self.assertFalse(reopened.claim())
        finally: state.close()
    def test_model_is_checked_with_key_header_not_url(self):
        opener = Sequence({'models': [{'name': PREFERRED[0], 'supportedGenerationMethods': ['generateContent']}]})
        client = Gemini('synthetic-key', 'Prompt', opener)
        self.assertEqual(client.select_model(), PREFERRED[0])
        request, timeout = opener.calls[0]
        self.assertNotIn('synthetic-key', request.full_url)
        self.assertEqual(request.get_header('X-goog-api-key'), 'synthetic-key')
        self.assertEqual(request.get_method(), 'GET')

    def test_does_not_silently_choose_pro_or_unknown_flash(self):
        client = Gemini('dummy', 'Prompt', Sequence({'models': [{'name': 'models/gemini-pro', 'supportedGenerationMethods': ['generateContent']}]}))
        with self.assertRaises(GeminiError): client.select_model()

    def test_generation_has_no_history_budget_128_and_no_thinking(self):
        opener = Sequence(ANSWER)
        client = Gemini('synthetic-key', 'Tiếng Việt', opener); client.model = PREFERRED[0]
        self.assertEqual(client.generate('Câu hỏi hiện tại'), 'Xin chào. Tôi có thể hỗ trợ bạn.')
        request, timeout = opener.calls[0]
        body = json.loads(request.data)
        self.assertEqual(body['generationConfig']['maxOutputTokens'], 128)
        self.assertEqual(body['generationConfig']['thinkingConfig'], {'thinkingBudget': 0})
        self.assertEqual(body['contents'], [{'role': 'user', 'parts': [{'text': 'Câu hỏi hiện tại'}]}])
        self.assertNotIn('synthetic-key', request.full_url)

    def test_output_enforced_max50_words_two_sentences(self):
        self.assertEqual(compact('Một. Hai. Ba.'), 'Một. Hai.')
        self.assertEqual(len(compact(' '.join(['từ']*80)).split()), 50)

    def test_timeout_is_sanitized_and_not_retried(self):
        opener = Sequence(urllib.error.URLError(TimeoutError('secret-key-url')))
        client = Gemini('secret-key', 'Prompt', opener); client.model = PREFERRED[0]
        with self.assertRaises(GeminiError) as result: client.generate('question')
        self.assertEqual(result.exception.kind, 'timeout')
        self.assertNotIn('secret', str(result.exception))
        self.assertEqual(len(opener.calls), 1)

    def test_blocked_answer_or_thought_only_not_forwarded(self):
        for answer in ({'candidates': []}, {'candidates': [{'finishReason': 'SAFETY'}]},
                       {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'thought': True, 'text': 'reasoning'}]}}]}):
            client = Gemini('dummy', 'Prompt', Sequence(answer)); client.model = PREFERRED[0]
            with self.assertRaises(GeminiError): client.generate('question')

    def test_bridge_limits_three_and_sends_generated_answer(self):
        class Generator:
            def generate(self, question): return 'Đáp án ngắn.'
        class Zalo:
            def __init__(self): self.sent = []
            def sendMessage(self, group, text):
                self.sent.append((group, text)); return {'message_id': 'synthetic-ack'}
        zalo = Zalo(); bridge = AIForwarder(Generator(), zalo, lambda: True)
        bridge.question = 'question'
        for _ in range(3): bridge.sendMessage('group', 'old fixed text')
        with self.assertRaises(GeminiError): bridge.sendMessage('group', 'old fixed text')
        self.assertEqual(zalo.sent, [('group', 'Đáp án ngắn.')]*3)

    def test_off_during_generation_prevents_zalo_send(self):
        active = [True]
        class Generator:
            def generate(self, question): active[0] = False; return 'answer'
        class Zalo:
            def sendMessage(self, *args): raise AssertionError('Must not send')
        bridge = AIForwarder(Generator(), Zalo(), lambda: active[0]); bridge.question = 'question'
        with self.assertRaises(GeminiError): bridge.sendMessage('group', 'fixed')

    def test_http_429_reports_number_without_error_body(self):
        error = urllib.error.HTTPError('https://example.invalid/private', 429, 'private-message', {}, None)
        client = Gemini('private-key', 'Prompt', Sequence(error))
        with self.assertRaises(GeminiError) as result: client.select_model()
        self.assertEqual(result.exception.code, 429)
        self.assertEqual(result.exception.kind, 'http')
        self.assertNotIn('private', str(result.exception))
