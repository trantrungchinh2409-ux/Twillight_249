"""A/B receive-only capture. Full events stay encrypted locally; never send."""
from datetime import datetime, timezone
import json
import re
import secrets
import sys
from .official_api import OfficialAPI, Transport, APIError
from .polling_test import TokenLock, ReadOnlyTransport, Redactor, receive_one, webhook_enabled
from .webhook_switch import RUNTIME, hidden, protect


def features(event, bot_id):
    message = event.get('message', {})
    text = message.get('text', '')
    if not isinstance(text, str):
        text = ''
    # These are observations only, never a trigger for automatic sending.
    return {'has_at_character': '@' in text,
            'contains_bot_display_text': '@bot jat design' in text.casefold(),
            'contains_bot_id_in_text': bool(bot_id) and bot_id in text,
            'has_angle_at_markup': bool(re.search(r'<@[^>]+>', text)),
            'message_keys': [k for k in message if re.fullmatch(r'[a-z][a-z0-9_]{0,35}', k)],
            'is_bot_sender': message.get('from', {}).get('is_bot')}


def main():
    print('ĐỐI CHIẾU A/B — chỉ nhận, KHÔNG gửi, KHÔNG đổi webhook.')
    print('Mẫu đầy đủ lưu mã hóa DPAPI tại runtime, không chia sẻ file .bin.')
    print('Dùng nội dung thử không riêng tư. Đóng mọi poller khác trước.')
    if not sys.stdin.isatty():
        return 2
    try:
        token = hidden('Bot Token (ẩn): ').strip()
        if not token:
            return 2
        with TokenLock(token):
            transport = ReadOnlyTransport(Transport(token))
            bot_id = OfficialAPI(transport).getMe()
            if webhook_enabled(transport):
                print('Webhook đang bật; dừng, không thay đổi.')
                return 3
            RUNTIME.mkdir(exist_ok=True)
            comparison = {}
            for label, instruction in (
                    ('A', 'Chọn @Bot JAT Design thật và gửi: thu A'),
                    ('B', 'Reply câu đã gửi của BOT, không @bot, nội dung: thu B')):
                input('Nhấn Enter khi sẵn sàng thử '+label+' (chưa gửi Zalo): ')
                print('ON — '+instruction)
                event = receive_one(transport, stop_on_error=True)
                if event is None:
                    print('OFF — chưa thu được '+label+'. Không tự thử lại.')
                    return 1
                if event['message']['chat']['chat_type'] != 'GROUP':
                    print('Nhận PRIVATE, chưa phải phép thử nhóm. Dừng, không gửi.')
                    return 1
                name = 'mention_compare_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+secrets.token_hex(3)+'_'+label
                encrypted = protect(json.dumps(event, ensure_ascii=False).encode('utf-8'))
                path = RUNTIME/(name+'.bin')
                path.write_bytes(encrypted)
                assert protect(path.read_bytes(), decrypt=True) == json.dumps(event, ensure_ascii=False).encode('utf-8')
                report = {'label': label, 'features': features(event, bot_id),
                          'schema': Redactor(bot_id).clean(event), 'automatic_reply_enabled': False}
                (RUNTIME/(name+'.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                comparison[label] = report['features']
                print('OFF — đã thu '+label+', chưa gửi tin. Tệp đối chiếu: '+name+'.json')
            print('Đã thu đủ A/B. Chờ đối chiếu trước khi bật tự động.')
            return 0
    except KeyboardInterrupt:
        print('\nOFF — đã dừng, không gửi tin.')
        return 130
    except APIError as error:
        print('OFF — loại=%s, mã=%s. Không tự thử lại.' % (error.kind, error.code))
        return 1
    except Exception:
        print('OFF — chưa hoàn tất; chi tiết nhạy cảm đã ẩn. Không gửi tin.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
