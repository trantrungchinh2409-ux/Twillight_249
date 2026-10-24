"""Explicitly approved one-attempt send to a user-selected group, not mention parsing."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys
from .official_api import APIError, OfficialAPI, Transport
from .polling_test import TokenLock, ReadOnlyTransport, receive_one, webhook_enabled, valid_event
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


def send_once(api, state, bot_id, event, marker, on_error=None):
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
    except Exception as error:
        state.mark(bot_key, APPROVAL, 'uncertain')
        state.mark(bot_key, event_key, 'uncertain')
        if on_error is not None:
            on_error({'phase': 'send_error',
                      'kind': error.kind if isinstance(error, APIError) else 'unknown',
                      'code': error.code if isinstance(error, APIError) else None})
        return 'uncertain'
    state.mark(bot_key, APPROVAL, 'api_acknowledged:'+digest(ack['message_id']))
    state.mark(bot_key, event_key, 'api_acknowledged')
    return 'api_acknowledged'


def preflight(transport, status, output=print):
    output('KIỂM TRA getUpdates — chưa gửi tin thử vào nhóm. Có thể chờ khoảng 80 giây.')
    for number in (1, 2):
        status({'phase': 'preflight_pending', 'check': number})
        try:
            result = transport.post('getUpdates', {'timeout': '30'}, timeout=40)
            if result != {} and not valid_event(result):
                raise APIError('Unexpected event contract', kind='api')
        except APIError as error:
            status({'phase': 'preflight_failed', 'kind': error.kind, 'code': error.code})
            output('OFF — getUpdates lỗi: loại=%s, mã=%s. Không thử lại, không gửi tin.' %
                   (error.kind, error.code if error.code is not None else 'không có'))
            return False
        # Events already queued are consumed only as connection evidence. The new
        # trigger nonce is not created yet; no preflight event can cause a send.
        status({'phase': 'preflight_passed', 'check': number})
        output('getUpdates: lần %s/2 thành công.' % number)
    return True


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
                counts = {'poll_errors': 0, 'rejected_events': 0}
                def record_poll(detail):
                    if detail['phase'] == 'poll_error':
                        counts['poll_errors'] += 1
                    if detail['phase'] == 'event_rejected_by_send_filter':
                        counts['rejected_events'] += 1
                    safe_status = dict(counts, last=detail,
                                       at_utc=datetime.now(timezone.utc).isoformat())
                    (RUNTIME/'one_shot_poll_status.json').write_text(
                        json.dumps(safe_status, ensure_ascii=False), encoding='utf-8')
                if not preflight(ReadOnlyTransport(transport), record_poll):
                    return 1
                marker = 'JAT-'+secrets.token_hex(8).upper()
                print('ON — Hai lần getUpdates đã đạt. Bây giờ trong ĐÚNG NHÓM đã thử A, @bot kèm mã:')
                print(marker)
                print('Chỉ gửi một tin có mã. Chờ tối đa khoảng 5 phút; lỗi đầu tiên sẽ dừng.')
                event = receive_one(ReadOnlyTransport(transport),
                                    accept=lambda e: eligible(e, bot_id, marker),
                                    on_status=record_poll, stop_on_error=True)
                if event is None:
                    print('OFF — Chưa có tin nhóm khớp mã; không gửi.')
                    return 1
                def record_send_error(detail):
                    record_poll(detail)
                    print('sendMessage lỗi: loại=%s, mã=%s; kết quả chưa chắc chắn, không gửi lại.' %
                          (detail['kind'], detail['code'] if detail['code'] is not None else 'không có'))
                outcome = send_once(api, state, bot_id, event, marker, on_error=record_send_error)
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
    except APIError as error:
        print('OFF — API lỗi: loại=%s, mã=%s. Không tự thử lại.' %
              (error.kind, error.code if error.code is not None else 'không có'))
        return 1
    except Exception:
        print('OFF — Chưa xác nhận hoàn tất; chi tiết nhạy cảm đã ẩn. Không tự gửi lại.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
