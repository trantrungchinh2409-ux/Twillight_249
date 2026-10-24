"""Official POST endpoints verified from docs.zaloplatforms.com on 2026-10-23.

Group mention metadata is NOT documented in the pages inspected. Group updates
fail closed, including if an unverified 'mentions' field happens to be present.
"""
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from .core import Event

BASE_URL = 'https://bot-api.zaloplatforms.com'


class ContractNotVerified(RuntimeError):
    pass


class APIError(RuntimeError):
    """Safe messages only; never forward transport URL, body or description."""

    def __init__(self, message, code=None, kind='unknown'):
        super().__init__(message)
        self.code = code if type(code) is int else None
        self.kind = kind if kind in ('unknown', 'http', 'api', 'timeout', 'tls',
                                     'network', 'invalid_json', 'redirect') else 'unknown'


class ProtocolError(APIError):
    pass


class MentionContractNotVerified(ContractNotVerified):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise APIError('Redirect rejected', kind='redirect')


class Transport:
    def __init__(self, token, opener=None):
        if not isinstance(token, str) or not token.strip() or token != token.strip():
            raise ValueError('A nonempty bot token is required')
        self._token = token
        self._opener = opener or urllib.request.build_opener(NoRedirect())

    def post(self, method, payload, timeout):
        if method not in ('getMe', 'getUpdates', 'sendMessage', 'getWebhookInfo',
                          'deleteWebhook', 'setWebhook'):
            raise ValueError('Unsupported API method')
        token = urllib.parse.quote(self._token, safe='')
        request = urllib.request.Request(
            BASE_URL + '/bot' + token + '/' + method,
            data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'JAT-Design/0.1'},
            method='POST')
        try:
            with self._opener.open(request, timeout=timeout) as response:
                data = response.read(1048577)
            if len(data) > 1048576:
                raise ProtocolError('API response too large')
            body = json.loads(data.decode('utf-8'))
        except urllib.error.HTTPError as error:
            raise APIError('HTTP rejected; details hidden', error.code, 'http') from None
        except APIError:
            raise
        except (TimeoutError, ssl.SSLError, urllib.error.URLError) as error:
            reason = error.reason if isinstance(error, urllib.error.URLError) else error
            kind = ('timeout' if isinstance(reason, TimeoutError) else
                    'tls' if isinstance(reason, ssl.SSLError) else 'network')
            raise APIError('Transport failed; details hidden', kind=kind) from None
        except (json.JSONDecodeError, UnicodeError):
            raise APIError('Invalid JSON; details hidden', kind='invalid_json') from None
        except Exception:
            # HTTPError/URLError may contain the token-bearing request URL.
            raise APIError('API transport or JSON failure; request details hidden') from None
        if not isinstance(body, dict) or body.get('ok') is not True:
            code = body.get('error_code') if isinstance(body, dict) else None
            if code is None and isinstance(body, dict):
                code = body.get('error')
            # Zalo getUpdates uses API error_code=408 for an empty long poll.
            # This is a parsed API response, NOT HTTP 408 or a socket timeout.
            if method == 'getUpdates' and type(code) is int and code == 408:
                return {}
            raise APIError('API rejected request; response details hidden', code, 'api')
        if method == 'deleteWebhook' and body.get('result') is True:
            return True
        if not isinstance(body.get('result'), dict):
            raise ProtocolError('Expected documented result object')
        return body['result']


def parse_event(result):
    if result.get('event_name') not in (
            'message.text.received', 'message.image.received',
            'message.sticker.received', 'message.voice.received',
            'message.unsupported.received'):
        raise ProtocolError('Unknown event contract')
    if result['event_name'] != 'message.text.received':
        return None
    message = result.get('message')
    if not isinstance(message, dict):
        raise ProtocolError('Missing message object')
    chat, sender = message.get('chat'), message.get('from')
    if not isinstance(chat, dict) or not isinstance(sender, dict):
        raise ProtocolError('Missing chat or sender object')
    kind = chat.get('chat_type')
    if kind == 'GROUP':
        # Official group guide says BOTH mentions and quoted replies arrive.
        # It does not document how to distinguish them in JSON. Never guess.
        raise MentionContractNotVerified('Group mention wire metadata not verified')
    if kind != 'PRIVATE':
        raise ProtocolError('Unknown chat type')
    values = (message.get('message_id'), chat.get('id'), sender.get('id'),
              message.get('text'))
    if not all(isinstance(v, str) and v.strip() for v in values):
        raise ProtocolError('Missing text message fields')
    if not isinstance(sender.get('is_bot'), bool):
        raise ProtocolError('Missing sender bot flag')
    return Event(values[0], values[1], 'private', values[2],
                 sender['is_bot'], (), values[3])


class OfficialAPI:
    def __init__(self, transport):
        self.transport = transport

    def getMe(self):
        result = self.transport.post('getMe', {}, timeout=15)
        if not isinstance(result.get('id'), str) or not result['id'].strip():
            raise ProtocolError('Missing bot identity')
        return result['id']

    def getUpdates(self):
        # Docs table says String; code sample uses numeric 30. Use table type.
        result = self.transport.post('getUpdates', {'timeout': '30'}, timeout=40)
        return parse_event(result)

    def sendMessage(self, chat_id, text):
        if not isinstance(chat_id, str) or not chat_id.strip():
            raise ValueError('Chat ID required')
        if not isinstance(text, str) or not 1 <= len(text) <= 2000:
            raise ValueError('Message must contain 1..2000 characters')
        result = self.transport.post('sendMessage', {'chat_id': chat_id, 'text': text}, timeout=15)
        if not isinstance(result.get('message_id'), str) or not result['message_id']:
            raise ProtocolError('Send acknowledgement missing message ID')
        return result
