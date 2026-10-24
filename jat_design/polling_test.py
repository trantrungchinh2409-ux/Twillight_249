"""Receive one real event. No message send or webhook mutation in this mode."""
import ctypes
import getpass
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
import secrets
import sys
import time
import warnings
from datetime import datetime, timezone
from .official_api import APIError, OfficialAPI, ProtocolError, Transport

EVENTS = {'message.text.received', 'message.image.received',
          'message.sticker.received', 'message.voice.received',
          'message.unsupported.received'}
LABELS = {'A': 'mention_bot', 'B': 'reply_without_mention',
          'C': 'mention_other', 'D': 'plain_text', 'E': 'other'}
KEYS = set(('event_name message from chat id display_name is_bot chat_type '
            'text message_id date mentions mention user_id bot_id offset length '
            'type reply_to_message reply_to quote quoted_message sender_id '
            'target_id entities data photo caption sticker voice_url url '
            'message_type event_type interaction_type trigger_type is_mentioned is_reply').split())


class ReadOnlyTransport:
    def __init__(self, transport):
        self.transport = transport

    def post(self, method, payload, timeout):
        if method not in ('getMe', 'getWebhookInfo', 'getUpdates'):
            raise ValueError('Receive-only test refuses mutation')
        return self.transport.post(method, payload, timeout)


class TokenLock:
    """Same token cannot run twice in the same Windows login session."""
    def __init__(self, token):
        self.name = 'Local\\JATDesignPolling_' + hashlib.sha256(token.encode()).hexdigest()

    def __enter__(self):
        if os.name != 'nt':
            raise RuntimeError('Windows required')
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
        api.CreateMutexW.restype = ctypes.c_void_p
        api.CloseHandle.argtypes = [ctypes.c_void_p]
        api.CloseHandle.restype = ctypes.c_bool
        ctypes.set_last_error(0)
        handle = api.CreateMutexW(None, False, self.name)
        if not handle:
            raise RuntimeError('Cannot create lock')
        if ctypes.get_last_error() == 183:
            api.CloseHandle(handle)
            raise RuntimeError('Another test for this bot is open')
        self.handle, self.api = handle, api
        return self

    def __exit__(self, *args):
        self.api.CloseHandle(self.handle)


def webhook_enabled(transport):
    result = transport.post('getWebhookInfo', {}, timeout=15)
    if not isinstance(result, dict) or not isinstance(result.get('url'), str):
        raise ProtocolError('Webhook state unknown; polling blocked')
    return bool(result['url'].strip())


def valid_event(result):
    if (not isinstance(result, dict) or not isinstance(result.get('event_name'), str)
            or result['event_name'] not in EVENTS):
        return False
    message = result.get('message')
    return (isinstance(message, dict) and
            isinstance(message.get('message_id'), str) and bool(message['message_id']) and
            isinstance(message.get('chat'), dict) and
            message['chat'].get('chat_type') in ('GROUP', 'PRIVATE'))


class Redactor:
    def __init__(self, bot_id):
        self.bot_id, self.salt = bot_id, secrets.token_bytes(32)

    def clean(self, value, key='', depth=0):
        if depth > 8:
            return '<depth_limit>'
        if isinstance(value, dict):
            return {name if (name in KEYS or
                            (key == 'message' and re.fullmatch(r'[a-z][a-z0-9_]{0,35}', name)))
                    else 'unknown_field_'+str(index):
                    self.clean(item, name, depth+1)
                    for index, (name, item) in enumerate(list(value.items())[:60])}
        if isinstance(value, list):
            return [self.clean(item, key, depth+1) for item in value[:30]]
        if isinstance(value, str):
            if depth == 2 and key not in KEYS:
                return '<metadata_sha256_' + hashlib.sha256(value.encode()).hexdigest() + '>'
            if key in ('message_type', 'event_type', 'interaction_type', 'trigger_type'):
                # Preserve only closed enum words; no arbitrary metadata strings.
                if value in ('TEXT', 'MENTION', 'REPLY', 'QUOTE', 'GROUP_MENTION',
                             'text', 'mention', 'reply', 'quote', 'group_mention'):
                    return value
                return '<metadata_sha256_' + hashlib.sha256(value.encode()).hexdigest() + '>'
            if key == 'event_name' and value in EVENTS:
                return value
            if key == 'chat_type' and value in ('GROUP', 'PRIVATE'):
                return value
            if key == 'id' or key.endswith('_id'):
                if value == self.bot_id:
                    return '<bot_id>'
                return '<id_'+hmac.new(self.salt, value.encode(), hashlib.sha256).hexdigest()[:12]+'>'
            return '<string>'
        if isinstance(value, bool) or value is None:
            return value
        return '<number>' if isinstance(value, (int, float)) else '<value>'


def receive_one(transport, seconds=300, clock=time.monotonic, wait=time.sleep, output=print,
                accept=None, on_status=None, stop_on_error=False):
    deadline, errors = clock()+seconds, 0
    while clock() < deadline:
        try:
            result = transport.post('getUpdates', {'timeout': '30'}, timeout=40)
        except APIError as error:
            detail = {'phase': 'poll_error', 'kind': error.kind, 'code': error.code}
            if on_status is not None:
                on_status(detail)
            output('Lỗi getUpdates: loại=%s, mã=%s. Đây không phải kết quả nhận rỗng.' %
                   (error.kind, error.code if error.code is not None else 'không có'))
            if stop_on_error:
                output('OFF — Dừng ở lỗi đầu tiên; không tự thử lại.')
                return None
            if error.code in (400, 401, 403, 404, 409):
                output('Dừng: API từ chối yêu cầu, mã %s. Không đổi token/webhook.' % error.code)
                return None
            errors += 1
            if errors >= 3:
                output('Dừng sau 3 lỗi liên tiếp. Chi tiết nhạy cảm đã ẩn.')
                return None
            delay = 30 if error.code == 429 else 2**errors
            output('Đợi %s giây trước lần thử lại có giới hạn.' % delay)
            wait(min(delay, max(0, deadline-clock())))
            continue
        errors = 0
        if valid_event(result):
            if accept is not None and not accept(result):
                output('ĐÃ NHẬN sự kiện nhưng không đạt điều kiện gửi; không gọi sendMessage.')
                if on_status is not None:
                    on_status({'phase': 'event_rejected_by_send_filter'})
                wait(min(0.25, max(0, deadline-clock())))
                continue
            if on_status is not None:
                on_status({'phase': 'event_accepted'})
            return result
        if result not in ({}, None):
            output('Dữ liệu chưa khớp hợp đồng sự kiện; không coi là thành công.')
            return None
        wait(min(1, max(0, deadline-clock())))
    output('Hết thời gian, chưa nhận sự kiện hợp lệ. Không gửi tin nào.')
    return None


def main():
    if sys.version_info < (3, 10):
        print('Cần Python 3.10 trở lên trên Windows 11.')
        return 2
    print('JAT Design — nhận sự kiện thật. TRẢ LỜI: OFF. Ctrl+C để dừng.')
    print('Token chỉ ở RAM trong phiên này. Không lưu token hoặc nội dung chat.')
    try:
        if not sys.stdin.isatty():
            print('Mở START_TEST.bat trực tiếp để nhập token ẩn.')
            return 2
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            token = getpass.getpass('Dán Bot Token tại đây (ẩn), rồi Enter: ').strip()
        if not token:
            print('Chưa nhập token; đã dừng.')
            return 2
        with TokenLock(token):
            transport = ReadOnlyTransport(Transport(token))
            bot_id = OfficialAPI(transport).getMe()
            print('getMe: API chấp nhận token. Chưa chứng minh nhận tin.')
            if webhook_enabled(transport):
                print('WEBHOOK ĐANG BẬT. Đã dừng; không polling hoặc xóa webhook.')
                print('Báo Codex: Webhook đang bật, để duyệt bước chuyển và khôi phục.')
                return 3
            redactor = Redactor(bot_id)
            print('Webhook không có URL. Nhận một sự kiện, tối đa khoảng 5 phút.')
            print('A: @bot thật | B: reply không @ | C: @người khác | D: tin thường | E: khác')
            label = input('Chọn A/B/C/D/E trước khi gửi trong Zalo: ').strip().upper()
            if label not in LABELS:
                print('Nhãn không hợp lệ; dừng, chưa polling.')
                return 2
            print('ON — Đang chờ. Bây giờ gửi phép thử trong nhóm Zalo.')
            event = receive_one(transport)
            if event is None:
                return 1
            group = event['message']['chat']['chat_type'] == 'GROUP'
            report = {'received_at_utc': datetime.now(timezone.utc).isoformat(),
                      'source': 'official_getUpdates_live', 'tester_label': LABELS[label],
                      'group_event': group, 'reply_enabled': False,
                      'mention_verified': False, 'schema': redactor.clean(event)}
            runtime = Path(__file__).resolve().parents[1] / 'runtime'
            runtime.mkdir(exist_ok=True)
            path = runtime / ('event_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+
                              '_'+secrets.token_hex(3)+'.json')
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print('ĐÃ NHẬN SỰ KIỆN THẬT: '+('GROUP' if group else 'PRIVATE (chưa đạt mục tiêu nhóm)'))
            print('Mẫu đã che: '+str(path))
            print('OFF — Dừng sau một sự kiện. Không trả lời; mention chưa xác minh.')
            return 0
    except KeyboardInterrupt:
        print('\nOFF — Đã dừng. Không đổi webhook, không gửi tin.')
        return 130
    except (APIError, ValueError, EOFError, getpass.GetPassWarning):
        print('Không hoàn thành kiểm tra API/nhập token. Chi tiết nhạy cảm đã ẩn.')
        return 1
    except (OSError, RuntimeError):
        print('Không mở được khóa/lưu kết quả. Đóng bản thử khác và kiểm tra quyền thư mục.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
