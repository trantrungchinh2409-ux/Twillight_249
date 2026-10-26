"""Windows launcher for stored Gemini keys and persistent local AI limits."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
import time
from .auto_reply import Controls, verified_group
from .gemini_client import GeminiError
from .key_vault import Vault, KeyPool, VAULT_LOCK
from .managed_limits import ManagedResponder
from .official_api import APIError, OfficialAPI, Transport
from .polling_test import TokenLock, ReadOnlyTransport, receive_one, webhook_enabled
from .state import State
from .safe_audit import record
from .reconnect import read_with_reconnect, retryable, wait
from .webhook_switch import RUNTIME, hidden
from .startup_check import StartupError, emit, ready, profile as check_profile


def status_text(snapshot, provider_until=0, now=None, key_status=None):
    now = time.time() if now is None else now
    local = max(0, snapshot.get('local_until', 0)-now)
    google = max(0, snapshot.get('google_until', 0)-now, provider_until-now)
    remaining = 0 if local else max(0, 10-sum(t > now-120 for t in snapshot.get('window_times', [])))
    keys = key_status or {}
    key_text = '; API đang chọn #%s (%s); dự phòng: %s' % (
        keys.get('active', '?'), keys.get('active_status', 'not_checked'), ', '.join('#%s=%s' % (k['number'], k['status'])
        for k in keys.get('keys', []) if not k['primary']) or 'không có')
    return 'STATUS — còn %s/10 lượt trong 2 phút; nghỉ nội bộ %ss; chờ Google %ss; khóa gửi chưa rõ: %s.' % (
        remaining, int(local+0.999), int(google+0.999), snapshot.get('uncertain', False))+key_text


def keyboard(controls, status):
    while not controls.snapshot()[1]:
        line = sys.stdin.readline()
        command = line.strip().upper() if line else 'QUIT'
        if command == 'STATUS': print(status(), flush=True); continue
        if command not in ('ON', 'OFF', 'QUIT', 'Q'):
            print('Nhập ON / OFF / STATUS / QUIT rồi Enter.'); continue
        active = controls.command(command)
        print('ON — sẵn sàng nhận tin mới.' if active else 'OFF — không bắt đầu gửi mới.', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', type=Path, default=Path(__file__).resolve().parents[1]/'SYSTEM_PROMPT.txt')
    args = parser.parse_args()
    print('JAT AI — khóa DPAPI, mặc định OFF, 10 lượt/2 phút, nghỉ 5 phút. Không lưu lịch sử nhóm.')
    if not sys.stdin.isatty(): return 2
    controls, state = Controls(), None
    stage = 'PROMPT'
    try:
        prompt = args.prompt.read_text(encoding='utf-8-sig').strip()
        if not prompt or len(prompt) > 4000: raise ValueError('Invalid prompt')
        stage = 'VAULT_LOCK'
        with TokenLock(VAULT_LOCK):
            result = ready(RUNTIME, args.prompt)
            if result: return result
            stage = 'VAULT_READ'
            if (RUNTIME/'profile-import.pending').exists():
                print('OFF — chuyển hồ sơ chưa hoàn tất. Giữ dữ liệu và báo Codex.'); return 4
            vault = Vault(RUNTIME/'gemini_keys.dpapi')
            if not vault.data['items']:
                print('Chưa có khóa đã lưu. Đóng cửa sổ và mở SETUP_API.bat trước.'); return 2
            print('Đã đọc %s khóa mã hóa. Không kiểm hàng loạt hoặc gọi Gemini khi khởi động.' % len(vault.data['items']))
            pool = KeyPool(vault, prompt)
            stage = 'TOKEN_INPUT'
            token = hidden('Bot Token Zalo (ẩn): ').strip()
            if not token: return 2
            stage = 'BOT_LOCK'
            with TokenLock(token):
                stage = 'ZALO_INIT'
                transport = Transport(token)
                zalo = OfficialAPI(transport)
                bot_id = read_with_reconnect(zalo.getMe)
                if read_with_reconnect(lambda: webhook_enabled(ReadOnlyTransport(transport))):
                    print('Webhook đang bật; dừng, không thay đổi.'); return 3
                stage = 'PROFILE_INVALID'
                check_profile(RUNTIME, bot_id)
                group_id = verified_group(RUNTIME, bot_id)
                stage = 'STATE_INIT'
                state = State(RUNTIME/'ai_reply.db')
                engine = ManagedResponder(state, bot_id, group_id)
                if engine.blocked():
                    print('OFF — có lần gửi chưa rõ từ phiên trước. Giữ DB và báo Codex.'); return 4
                stage = 'STARTUP_UNKNOWN'
                cache, lock = {}, threading.Lock()
                def refresh():
                    with lock:
                        cache['snapshot'] = engine.status()
                        cache['provider_until'] = time.time()+pool.wait_remaining()
                        cache['keys'] = pool.status()
                def status():
                    with lock: return status_text(cache['snapshot'], cache['provider_until'], key_status=cache['keys'])
                refresh()
                record('start', active=pool.status()['active'])
                print(status())
                print('ON / OFF / STATUS / QUIT rồi Enter. Chỉ nhóm thử đã xác minh.')
                threading.Thread(target=keyboard, args=(controls, status), daemon=True).start()
                poll_failures = 0
                while True:
                    refresh()
                    on, quit_now, armed = controls.snapshot()
                    if quit_now: return 0
                    if not on:
                        time.sleep(0.2); continue
                    errors = []
                    def poll_output(message):
                        if message.startswith('OFF — Dừng ở lỗi đầu tiên') and errors and retryable(errors[-1]):
                            message = 'Kết thúc lượt đọc hiện tại; sẽ xét kết nối lại.'
                        print(message, flush=True)
                    event = receive_one(ReadOnlyTransport(transport), seconds=35, stop_on_error=True, output=poll_output,
                        on_status=lambda s: errors.append(s) if s.get('phase') == 'poll_error' else None)
                    if errors:
                        detail = errors[-1]
                        if not retryable(detail): return 1
                        poll_failures += 1
                        delay = 60 if detail.get('code') == 429 else min(60, 5*2**min(poll_failures-1, 4))
                        record('poll_wait', kind=detail.get('kind'), code=detail.get('code'), seconds=delay)
                        print('Chờ kết nối đọc lại %ss; không gửi lại tin.' % delay, flush=True)
                        if not wait(delay, quit_now=lambda: controls.snapshot()[1]): return 0
                        continue
                    poll_failures = 0
                    if event is None: continue
                    active, quit_now, current_arm = controls.snapshot()
                    if quit_now or not active or current_arm != armed: continue
                    old_active = pool.status()['active']
                    outcome = engine.handle(zalo, pool, event, active, armed,
                                            still_on=lambda: controls.snapshot()[0])
                    refresh()
                    active_key = pool.status()['active']
                    if old_active != active_key: record('key_switch', active=active_key)
                    record('result', active=active_key, outcome=outcome)
                    report = {'at_utc': datetime.now(timezone.utc).isoformat(), 'outcome': outcome,
                              'remaining': cache['snapshot']['remaining'], 'model': pool.model,
                              'history_sent': False, 'maxOutputTokens': 128}
                    if engine.last_error:
                        report['error'] = engine.last_error
                        print('CMD lỗi riêng: %s' % json.dumps(engine.last_error), flush=True)
                    (RUNTIME/'managed_ai_status.json').write_text(json.dumps(report), encoding='utf-8')
                    print('AI: '+outcome+' — '+status(), flush=True)
                    if outcome == 'uncertain_blocked':
                        print('OFF — gửi chưa rõ kết quả, không tự gửi lại.'); return 1
                    if outcome == 'provider_error' and retryable(engine.last_error or {}):
                        print('Lỗi mạng/provider tạm thời; giữ ON, không gửi lại câu hỏi cũ và không đổi khóa.')
                        continue
                    if outcome in ('invalid_key', 'billing_problem', 'provider_error'):
                        print('OFF — kiểm tra khóa/thanh toán/kết nối trong CMD, không báo nạp tiền trong nhóm.'); return 1
    except KeyboardInterrupt:
        print('\nOFF — dừng, không tự gửi lại request đang diễn ra.'); return 130
    except StartupError as error:
        return emit(error.category, stage=stage)
    except APIError as error:
        print('OFF [ZALO_API] stage=%s loại=%s mã=%s; không in nội dung bí mật.' % (stage, error.kind, error.code)); return 1
    except Exception as error:
        return emit(stage, error=error, stage=stage)
    finally:
        controls.command('QUIT')
        if state is not None: state.close()


if __name__ == '__main__': raise SystemExit(main())
