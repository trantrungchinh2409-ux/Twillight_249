"""Opt-in exact-text auto reply. Reuses the proven API; no entity claims."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import threading
import time
from .official_api import APIError, OfficialAPI, Transport
from .polling_test import TokenLock, ReadOnlyTransport, receive_one, webhook_enabled
from .state import State
from .webhook_switch import RUNTIME, hidden, protect

TRIGGER = '@Bot JAT Design'
REPLY = 'JAT Design đã nhận tin!'
GROUP_SAMPLE = 'mention_compare_20261024T080236_974d67_A.bin'


def hashed(value):
    return hashlib.sha256(value.encode()).hexdigest()


def verified_group(runtime, bot_id):
    """Use the user's already captured group, never auto-learn another group."""
    path = runtime/'one_shot.db'
    db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    try:
        row = db.execute('SELECT status FROM deliveries WHERE chat_id=? AND event_id=?',
                         (hashed(bot_id), 'approved-single-send-20261024')).fetchone()
    finally:
        db.close()
    if not row or not row[0].startswith('api_acknowledged:'):
        raise ValueError('Token bot does not match the successful live test')
    event = json.loads(protect((runtime/GROUP_SAMPLE).read_bytes(), decrypt=True))
    message = event.get('message', {})
    chat = message.get('chat', {})
    if (event.get('event_name') != 'message.text.received' or chat.get('chat_type') != 'GROUP'
            or not isinstance(chat.get('id'), str) or not chat['id'].strip()
            or not isinstance(message.get('text'), str) or TRIGGER not in message['text']):
        raise ValueError('Verified group capture invalid')
    return chat['id']


class Controls:
    def __init__(self):
        self.lock = threading.Lock()
        self.enabled, self.quit, self.armed_ms = False, False, 0

    def command(self, value):
        with self.lock:
            if value == 'ON' and not self.enabled:
                self.armed_ms = time.time()*1000
                self.enabled = True
            elif value == 'OFF':
                self.enabled = False
            elif value in ('QUIT', 'Q'):
                self.enabled, self.quit = False, True
            return self.enabled

    def snapshot(self):
        with self.lock:
            return self.enabled, self.quit, self.armed_ms


class AutoResponder:
    def __init__(self, state, bot_id, group_id, clock=time.time):
        self.state, self.bot_id, self.group_id, self.clock = state, bot_id, group_id, clock
        self.attempts = 0
        self.last_error = None
        self.bot_key = hashed(bot_id)
        self.group_key = hashed(bot_id+'\0'+group_id)
        state.db.execute('CREATE TABLE IF NOT EXISTS auto_limits (k TEXT PRIMARY KEY, next_at REAL NOT NULL)')
        state.db.execute('CREATE TABLE IF NOT EXISTS auto_block (k TEXT PRIMARY KEY, reason TEXT NOT NULL)')
        state.db.commit()

    def blocked(self):
        return self.state.db.execute('SELECT 1 FROM auto_block WHERE k=?', (self.bot_key,)).fetchone() is not None

    def handle(self, api, event, enabled, armed_ms, still_on=lambda: True):
        if not enabled:
            return 'off'
        if self.attempts >= 5:
            return 'limit'
        if self.blocked():
            return 'uncertain_blocked'
        if not isinstance(event, dict) or event.get('event_name') != 'message.text.received':
            return 'ignored'
        message = event.get('message')
        if not isinstance(message, dict):
            return 'ignored'
        chat, sender = message.get('chat'), message.get('from')
        if not isinstance(chat, dict) or not isinstance(sender, dict):
            return 'ignored'
        if (chat.get('chat_type') != 'GROUP' or chat.get('id') != self.group_id
                or sender.get('is_bot') is not False or not isinstance(sender.get('id'), str)
                or not sender['id'].strip() or sender['id'] == self.bot_id
                or not isinstance(message.get('text'), str) or TRIGGER not in message['text']
                or not isinstance(message.get('message_id'), str) or not message['message_id'].strip()):
            return 'ignored'
        stamp = message.get('date')
        # Official samples use epoch milliseconds. Unknown units fail closed.
        if (type(stamp) not in (int, float) or not armed_ms <= stamp <= self.clock()*1000+60000):
            return 'old_or_unknown_time'
        event_key = hashed(message['message_id'])
        if not self.state.reserve(self.group_key, event_key):
            return 'duplicate'
        row = self.state.db.execute('SELECT next_at FROM auto_limits WHERE k=?', (self.group_key,)).fetchone()
        now = self.clock()
        if row and now < row[0]:
            self.state.mark(self.group_key, event_key, 'cooldown_skipped')
            return 'cooldown'
        if not still_on():
            self.state.mark(self.group_key, event_key, 'off_skipped')
            return 'off'
        # Durable cooldown and crash guard before entering the network call.
        with self.state.db:
            self.state.db.execute('INSERT OR REPLACE INTO auto_limits VALUES (?,?)', (self.group_key, now+10))
            self.state.db.execute('INSERT INTO auto_block VALUES (?,?)', (self.bot_key, 'send_pending_or_uncertain'))
        self.attempts += 1
        try:
            ack = api.sendMessage(self.group_id, REPLY)
            if not isinstance(ack, dict) or not isinstance(ack.get('message_id'), str) or not ack['message_id']:
                raise APIError('Missing send acknowledgement')
        except Exception as error:
            self.last_error = {'kind': error.kind, 'code': error.code} if isinstance(error, APIError) else {'kind': 'unknown', 'code': None}
            self.state.mark(self.group_key, event_key, 'uncertain')
            return 'uncertain_blocked'
        # If recording fails, leave the guard present, never resend automatically.
        self.state.mark(self.group_key, event_key, 'api_acknowledged')
        with self.state.db:
            self.state.db.execute('DELETE FROM auto_block WHERE k=?', (self.bot_key,))
        return 'sent'


def keyboard(controls):
    while not controls.snapshot()[1]:
        line = sys.stdin.readline()
        command = line.strip().upper() if line else 'QUIT'
        if command not in ('ON', 'OFF', 'QUIT', 'Q'):
            print('Chỉ nhập ON / OFF / QUIT rồi Enter.')
            continue
        active = controls.command(command)
        print('ON — sẵn sàng nhận tin mới.' if active else 'OFF — không bắt đầu gửi mới.')


def main():
    print('JAT AUTO — lọc chuỗi đúng, KHÔNG xác thực mention entity. Mặc định OFF.')
    print('Chỉ nhóm thử đã xác minh. Cooldown 10 giây, tối đa 5 lần gửi/phiên.')
    print('Đóng mọi poller khác. OFF không thu hồi được request gửi đang diễn ra.')
    if not sys.stdin.isatty():
        return 2
    controls = Controls()
    state = None
    try:
        token = hidden('Bot Token (ẩn): ').strip()
        if not token:
            return 2
        with TokenLock(token):
            transport = Transport(token)
            api = OfficialAPI(transport)
            bot_id = api.getMe()
            if webhook_enabled(ReadOnlyTransport(transport)):
                print('Webhook đang bật; dừng, không đổi cấu hình.')
                return 3
            group_id = verified_group(RUNTIME, bot_id)
            state = State(RUNTIME/'auto_reply.db')
            responder = AutoResponder(state, bot_id, group_id)
            if responder.blocked():
                print('OFF — có lần gửi chưa rõ kết quả từ phiên trước. Không tự mở khóa hoặc gửi lại.')
                return 4
            print('Nhóm/token khớp dữ liệu thử thành công. Nhập ON / OFF / QUIT rồi Enter.')
            threading.Thread(target=keyboard, args=(controls,), daemon=True).start()
            while True:
                on, quit_now, armed = controls.snapshot()
                if quit_now:
                    return 0
                if not on:
                    time.sleep(0.1)
                    continue
                errors = []
                event = receive_one(ReadOnlyTransport(transport), seconds=35, stop_on_error=True,
                                    on_status=lambda s: errors.append(s) if s.get('phase') == 'poll_error' else None)
                if errors:
                    controls.command('OFF')
                    return 1
                if event is None:
                    continue
                current_on, quit_now, current_armed = controls.snapshot()
                # Discard a request spanning OFF/ON; do not forward an old event.
                if quit_now or not current_on or current_armed != armed:
                    continue
                outcome = responder.handle(api, event, current_on, armed,
                                           still_on=lambda: controls.snapshot()[0])
                report = {'at_utc': datetime.now(timezone.utc).isoformat(), 'outcome': outcome,
                          'attempts': responder.attempts, 'limit': 5, 'cooldown_seconds': 10,
                          'filter': 'exact_text_substring', 'entity_verified': False}
                if responder.last_error is not None:
                    report['send_error'] = responder.last_error
                    print('sendMessage lỗi loại=%s, mã=%s; không tự gửi lại.' %
                          (responder.last_error['kind'], responder.last_error['code']))
                (RUNTIME/'auto_reply_status.json').write_text(json.dumps(report), encoding='utf-8')
                print('AUTO: %s — lần gửi %s/5.' % (outcome, responder.attempts))
                if outcome == 'uncertain_blocked' or responder.attempts >= 5:
                    controls.command('OFF')
                    print('OFF — đã dừng phiên, không gửi thêm.')
                    return 1 if outcome == 'uncertain_blocked' else 0
    except KeyboardInterrupt:
        print('\nOFF — đã dừng. Request gửi đang diễn ra có thể chưa rõ kết quả.')
        return 130
    except APIError as error:
        print('OFF — lỗi loại=%s, mã=%s. Không tự thử lại.' % (error.kind, error.code))
        return 1
    except Exception:
        print('OFF — cấu hình/bản ghi/khóa không hợp lệ; không gửi. Báo Codex kiểm tra.')
        return 1
    finally:
        controls.command('QUIT')
        if state is not None:
            state.close()


if __name__ == '__main__':
    raise SystemExit(main())
