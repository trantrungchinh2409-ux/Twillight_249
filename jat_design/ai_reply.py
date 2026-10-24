"""Gemini composition around unchanged AUTO engine. First test limited to 3 sends."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import threading
import time
from .auto_reply import AutoResponder, Controls, keyboard, verified_group, TRIGGER
from .gemini_client import Gemini, GeminiError
from .official_api import APIError, OfficialAPI, Transport
from .polling_test import TokenLock, ReadOnlyTransport, receive_one, webhook_enabled
from .state import State
from .webhook_switch import RUNTIME, hidden


class AIForwarder:
    def __init__(self, gemini, zalo, still_on):
        self.gemini, self.zalo, self.still_on = gemini, zalo, still_on
        self.question, self.attempts = '', 0
        self.stage = 'ready'

    def sendMessage(self, group, ignored_fixed_reply):
        if self.attempts >= 3 or not self.still_on():
            raise GeminiError('AI session disabled')
        self.attempts += 1
        self.stage = 'gemini'
        answer = self.gemini.generate(self.question)
        # OFF while Gemini is generating must prevent a new Zalo send.
        if not self.still_on():
            raise GeminiError('OFF during generation; no Zalo send')
        self.stage = 'zalo'
        result = self.zalo.sendMessage(group, answer)
        self.stage = 'acknowledged'
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prompt', type=Path, default=Path(__file__).resolve().parents[1]/'SYSTEM_PROMPT.txt')
    parser.add_argument('--test-only', action='store_true')
    args = parser.parse_args()
    print('JAT AI — mặc định OFF, tối đa 3 lần thử phản hồi Zalo/phiên. Không lưu lịch sử nhóm.')
    if not sys.stdin.isatty():
        return 2
    controls, state = Controls(), None
    try:
        prompt = args.prompt.read_text(encoding='utf-8-sig').strip()
        if not prompt or len(prompt) > 4000:
            print('SYSTEM_PROMPT cần 1–4000 ký tự.')
            return 2
        key = hidden('Gemini API Key (ẩn, không lưu): ').strip()
        gemini = Gemini(key, prompt)
        print('Đang kiểm tra model khả dụng bằng models.list...')
        print('Model đã kiểm tra: '+gemini.select_model())
        print('Kiểm thử Gemini riêng; không gửi câu này tới Zalo...')
        print('Gemini: '+gemini.generate('Chỉ trả lời một câu: Kiểm tra Gemini thành công.'))
        print('Gemini đã trả lời; chưa kiểm thử gửi AI vào Zalo.')
        if args.test_only:
            return 0
        token = hidden('Bot Token Zalo (ẩn): ').strip()
        with TokenLock(token):
            transport = Transport(token)
            zalo = OfficialAPI(transport)
            bot_id = zalo.getMe()
            if webhook_enabled(ReadOnlyTransport(transport)):
                print('Webhook đang bật; OFF, không sửa cấu hình.')
                return 3
            group_id = verified_group(RUNTIME, bot_id)
            state = State(RUNTIME/'ai_reply.db')
            engine = AutoResponder(state, bot_id, group_id)
            if engine.blocked():
                print('OFF — phiên AI trước có kết quả chưa rõ; không tự mở khóa.')
                return 4
            forwarder = AIForwarder(gemini, zalo, lambda: controls.snapshot()[0])
            print('Sẵn sàng. Nhập ON / OFF / QUIT rồi Enter. Chỉ hỏi trong nhóm thử đã xác minh.')
            threading.Thread(target=keyboard, args=(controls,), daemon=True).start()
            while True:
                on, quit_now, armed = controls.snapshot()
                if quit_now: return 0
                if not on:
                    time.sleep(0.1); continue
                errors = []
                event = receive_one(ReadOnlyTransport(transport), seconds=35, stop_on_error=True,
                                    on_status=lambda s: errors.append(s) if s.get('phase') == 'poll_error' else None)
                if errors: return 1
                if event is None: continue
                current_on, quit_now, current_armed = controls.snapshot()
                if quit_now or not current_on or armed != current_armed: continue
                text = event.get('message', {}).get('text', '')
                if not isinstance(text, str) or TRIGGER not in text: continue
                forwarder.question = text.replace(TRIGGER, '', 1).strip()
                if not forwarder.question:
                    print('Bỏ qua: chưa có câu hỏi sau tên bot.'); continue
                outcome = engine.handle(forwarder, event, current_on, armed,
                                        still_on=lambda: controls.snapshot()[0])
                forwarder.question = ''
                report = {'at_utc': datetime.now(timezone.utc).isoformat(), 'outcome': outcome,
                          'attempts': engine.attempts, 'limit': 3, 'stage': forwarder.stage,
                          'model': gemini.model, 'maxOutputTokens': 128, 'history_sent': False}
                if engine.last_error:
                    report['error'] = engine.last_error
                    print('AI lỗi tại %s: loại=%s, mã=%s. Không thử lại.' %
                          (forwarder.stage, engine.last_error['kind'], engine.last_error['code']))
                (RUNTIME/'ai_reply_status.json').write_text(json.dumps(report), encoding='utf-8')
                print('AI: %s — lần thử %s/3.' % (outcome, engine.attempts))
                if outcome == 'uncertain_blocked' or engine.attempts >= 3:
                    print('OFF — kết thúc phiên thử, không gửi thêm.')
                    return 1 if outcome == 'uncertain_blocked' else 0
    except KeyboardInterrupt:
        print('\nOFF — dừng, không tự gửi lại request chưa rõ kết quả.')
        return 130
    except APIError as error:
        print('OFF — loại=%s, mã=%s. Không tự thử lại.' % (error.kind, error.code))
        return 1
    except Exception:
        print('OFF — chưa hoàn tất; chi tiết nhạy cảm đã ẩn. Kiểm tra prompt/cấu hình.')
        return 1
    finally:
        controls.command('QUIT')
        if state is not None: state.close()


if __name__ == '__main__':
    raise SystemExit(main())
