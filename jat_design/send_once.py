"""Explicitly approved one-attempt send to a user-selected group, not mention parsing."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys
from .official_api import APIError, OfficialAPI, Transport
from .polling_test import TokenLock, ReadOnlyTransport, receive_one, webhook_enabled
from .state import State
from .webhook_switch import hidden

REPLY = 'JAT Design đã hoạt động thành công!'
APPROVAL = 'approved-single-send-20261024'
RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def eligible(result, bot_id, marker):
    if not isinstance(result, dict) or result.get('event_name') != 'message.text.received':
        return False
    message = result.get('message')
    if not isinstance(message, dict):
        return False
    chat, sender = message.get('chat'), message.get('from')
    if not isinstance(chat, dict) or not isinstance(sender, dict):
        return False
    values = (chat.get('id'), sender.get('id'), message.get('message_id'), message.get('text'))
    return (all(isinstance(v, str) and bool(v.strip()) for v in values)
            and chat.get('chat_type') == 'GROUP' and sender.get('is_bot') is False
            and sender['id'] != bot_id and chat['id'] != bot_id
            and isinstance(marker, str) and len(marker) >= 16
            and marker in message['text'].split())


def send_once(api, state, bot_id, event, marker):
    if not eligible(event, bot_id, marker):
        return 'ignored'
    bot_key = digest(bot_id)
    # One global approval per bot in this installation, not one send per event.
    # Durable reserve BEFORE any HTTP call; timeout/crash never releases approval.
    if not state.reserve(bot_key, APPROVAL):
        return 'already_attempted'
    message = event['message']
    event_key = digest(message['chat']['id']+'\0'+message['message_id'])
    if not state.reserve(bot_key, event_key):
        state.mark(bot_key, APPROVAL, 'blocked_duplicate')
        return 'duplicate'
    try:
        ack = api.sendMessage(message['chat']['id'], REPLY)
        if not isinstance(ack, dict) or not isinstance(ack.get('message_id'), str) or not ack['message_id']:
            raise APIError('No send acknowledgement')
    except Exception:
        state.mark(bot_key, APPROVAL, 'uncertain')
        state.mark(bot_key, event_key, 'uncertain')
        return 'uncertain'
    state.mark(bot_key, APPROVAL, 'api_acknowledged:'+digest(ack['message_id']))
    state.mark(bot_key, event_key, 'api_acknowledged')
    return 'api_acknowledged'


def main():
    print('JAT Design — MỘT LẦN GỬI đã được chủ dự án duyệt. Ctrl+C để dừng.')
    print('Đóng START_TEST/B và mọi poller khác trước khi tiếp tục.')
    print('Đây là chọn nhóm bằng mã thử, CHƯA xác minh parser mention/reply.')
    print('Câu sẽ gửi: '+REPLY)
    if not sys.stdin.isatty():
        print('Mở SEND_ONCE.bat trực tiếp để nhập token ẩn.')
        return 2
    try:
        token = hidden('Bot Token (ẩn, chỉ trong RAM): ').strip()
        if not token:
            return 2
        with TokenLock(token):
            transport = Transport(token)
            api = OfficialAPI(transport)
            bot_id = api.getMe()
            if webhook_enabled(ReadOnlyTransport(transport)):
                print('Webhook đang bật; dừng, không thay đổi webhook hoặc gửi tin.')
                return 3
            RUNTIME.mkdir(exist_ok=True)
            state = State(RUNTIME/'one_shot.db')
            try:
                row = state.db.execute('SELECT status FROM deliveries WHERE chat_id=? AND event_id=?',
                                       (digest(bot_id), APPROVAL)).fetchone()
                if row:
                    print('Đã có lần gửi/đặt chỗ trước. KHÔNG gửi lại. Giữ nguyên one_shot.db để kiểm tra.')
                    return 4
                marker = 'JAT-'+secrets.token_hex(8).upper()
                print('ON — Trong ĐÚNG NHÓM đã thử A, chọn @Bot JAT Design rồi gửi kèm mã này:')
                print(marker)
                print('Không đăng mã vào nhóm khác. Chờ tối đa khoảng 5 phút.')
                event = receive_one(ReadOnlyTransport(transport),
                                    accept=lambda e: eligible(e, bot_id, marker))
                if event is None:
                    print('OFF — Chưa có tin nhóm khớp mã; không gửi.')
                    return 1
                outcome = send_once(api, state, bot_id, event, marker)
                receipt = {'at_utc': datetime.now(timezone.utc).isoformat(), 'outcome': outcome,
                           'group_event': True, 'reply': REPLY, 'mention_verified': False,
                           'selection': 'fresh_user_marker_in_group', 'automatic_retry': False}
                (RUNTIME/'one_shot_receipt.json').write_text(
                    json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
                if outcome == 'api_acknowledged':
                    print('API sendMessage đã xác nhận message_id. OFF — Không gửi thêm.')
                    print('Hãy kiểm tra trong Zalo có đúng một câu trên; báo Codex kết quả nhìn thấy.')
                    return 0
                print('OFF — Kết quả: '+outcome+'. KHÔNG thử gửi lại, kể cả mở lại cửa sổ.')
                return 1
            finally:
                state.close()
    except KeyboardInterrupt:
        print('\nOFF — Đã dừng. Nếu đang gửi thì kết quả có thể chưa rõ; không tự gửi lại.')
        return 130
    except Exception:
        print('OFF — Chưa xác nhận hoàn tất; chi tiết nhạy cảm đã ẩn. Không tự gửi lại.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
