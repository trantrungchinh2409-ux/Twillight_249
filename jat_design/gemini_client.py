"""Small stateless Gemini REST client. API key is header-only, never logged."""
import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from .official_api import APIError, NoRedirect

PREFERRED = ('models/gemini-2.5-flash-lite', 'models/gemini-2.5-flash')
BASE = 'https://generativelanguage.googleapis.com/v1beta/'
RULES = ('Trả lời bằng tiếng Việt, ngắn gọn 1–2 câu, không quá 50 từ. '
         'Chỉ trả lời câu hỏi hiện tại. Không có lịch sử nhóm. Không xuất phần suy nghĩ.')


class GeminiError(APIError):
    pass


def compact(text):
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        raise GeminiError('Empty Gemini answer', kind='api')
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return ' '.join(' '.join(sentences[:2]).split()[:50])


class Gemini:
    def __init__(self, key, prompt, opener=None):
        if not isinstance(key, str) or not key.strip() or len(prompt) > 4000:
            raise ValueError('Key/prompt invalid')
        self.key, self.prompt, self.model = key.strip(), prompt, None
        self.opener = opener or urllib.request.build_opener(NoRedirect())

    def request(self, path, payload=None):
        request = urllib.request.Request(BASE+path,
            data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'x-goog-api-key': self.key, 'Content-Type': 'application/json'},
            method='GET' if payload is None else 'POST')
        try:
            with self.opener.open(request, timeout=30) as response:
                data = response.read(1048577)
            if len(data) > 1048576:
                raise GeminiError('Response too large')
            result = json.loads(data.decode('utf-8'))
        except urllib.error.HTTPError as error:
            raise GeminiError('Gemini HTTP failure; details hidden', error.code, 'http') from None
        except (TimeoutError, ssl.SSLError, urllib.error.URLError) as error:
            reason = error.reason if isinstance(error, urllib.error.URLError) else error
            kind = 'timeout' if isinstance(reason, TimeoutError) else 'tls' if isinstance(reason, ssl.SSLError) else 'network'
            raise GeminiError('Gemini transport failure; details hidden', kind=kind) from None
        except GeminiError:
            raise
        except Exception:
            raise GeminiError('Gemini response failure; details hidden', kind='invalid_json') from None
        if not isinstance(result, dict) or 'error' in result:
            code = result.get('error', {}).get('code') if isinstance(result, dict) and isinstance(result.get('error'), dict) else None
            raise GeminiError('Gemini API rejected request', code, 'api')
        return result

    def select_model(self):
        available, token = set(), None
        for _ in range(5):
            params = {'pageSize': 100}
            if token:
                params['pageToken'] = token
            result = self.request('models?'+urllib.parse.urlencode(params))
            for model in result.get('models', []):
                if isinstance(model, dict) and 'generateContent' in model.get('supportedGenerationMethods', []):
                    name = model.get('name')
                    if isinstance(name, str): available.add(name)
            token = result.get('nextPageToken')
            if not token: break
        self.model = next((name for name in PREFERRED if name in available), None)
        if self.model is None:
            raise GeminiError('No approved budget Flash model available; no silent fallback', kind='api')
        return self.model

    def generate(self, question):
        if self.model not in PREFERRED or not isinstance(question, str) or not question.strip():
            raise ValueError('Model/question missing')
        body = {'systemInstruction': {'parts': [{'text': self.prompt+'\n'+RULES}]},
                'contents': [{'role': 'user', 'parts': [{'text': question[:1200]}]}],
                'generationConfig': {'maxOutputTokens': 128, 'temperature': 0.3,
                                     'thinkingConfig': {'thinkingBudget': 0}}}
        result = self.request(self.model+':generateContent', body)
        candidates = result.get('candidates', [])
        if not isinstance(candidates, list) or not candidates:
            raise GeminiError('Gemini returned no answer', kind='api')
        candidate = candidates[0]
        if candidate.get('finishReason') not in ('STOP', 'MAX_TOKENS'):
            raise GeminiError('Gemini answer blocked/invalid', kind='api')
        parts = candidate.get('content', {}).get('parts', [])
        text = ' '.join(part['text'] for part in parts if isinstance(part, dict)
                        and isinstance(part.get('text'), str) and part.get('thought') is not True)
        return compact(text)
