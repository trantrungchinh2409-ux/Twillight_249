"""Linux/Railway entry point around the unchanged verified Windows engines.

Deployment preparation only: default OFF, no platform mutations, no billing.
"""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import threading
import time
from .auto_reply import AutoResponder, TRIGGER, hashed
from .ai_reply import AIForwarder, TrialQuota
from .gemini_client import Gemini
from .official_api import APIError, OfficialAPI, Transport
from .polling_test import ReadOnlyTransport, receive_one, webhook_enabled
from .state import State


def settings(env):
    if env.get('BOT_ENABLED', 'false') != 'true':
        return None
    if env.get('LOCAL_POLLERS_STOPPED') != 'true':
        raise ValueError('Local polling stop not confirmed')
    required = ('ZALO_BOT_TOKEN', 'GEMINI_API_KEY', 'ZALO_GROUP_ID', 'EXPECTED_BOT_ID_SHA256')
    if any(not env.get(name, '').strip() for name in required):
        raise ValueError('Missing secure deployment settings')
    data = Path(env.get('DATA_DIR', '/data'))
    mounted = env.get('RAILWAY_VOLUME_MOUNT_PATH')
    if not mounted or Path(mounted).resolve() != data.resolve() or not data.is_dir():
        raise ValueError('Persistent Railway volume required')
    expected = env['EXPECTED_BOT_ID_SHA256']
    if len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected):
        raise ValueError('Expected identity hash invalid')
    return data


class PollingLease:
    def __init__(self, path): self.path, self.stream = path, None
    def __enter__(self):
        import fcntl
        self.stream = self.path.open('a+b')
        try: fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            self.stream.close()
            raise RuntimeError('Another cloud poller holds the volume lock') from None
        return self
    def __exit__(self, *args):
        self.stream.close()


def hold(path, reason):
    path.write_text(json.dumps({'reason': reason, 'at_utc': datetime.now(timezone.utc).isoformat()}), encoding='utf-8')


def run(env, stop):
    data = settings(env)
    if data is None:
        print('CLOUD OFF — no API requests. No local polling may overlap with cloud ON.', flush=True)
        while not stop.wait(1): pass
        return 0
    with PollingLease(data/'polling.lock'):
        hold_file = data/'cloud_hold.json'
        if hold_file.exists():
            print('CLOUD OFF — persistent hold requires review; no API requests.', flush=True)
            while not stop.wait(1): pass
            return 0
        state = State(data/'ai_reply.db')
        try:
            transport = Transport(env['ZALO_BOT_TOKEN'])
            zalo = OfficialAPI(transport)
            bot_id = zalo.getMe()
            if hashed(bot_id) != env['EXPECTED_BOT_ID_SHA256']:
                raise ValueError('Bot identity mismatch')
            if webhook_enabled(ReadOnlyTransport(transport)):
                raise ValueError('Webhook active; no mutation allowed')
            engine = AutoResponder(state, bot_id, env['ZALO_GROUP_ID'])
            quota = TrialQuota(state, bot_id)
            if engine.blocked() or quota.used() >= 3:
                hold(hold_file, 'uncertain_or_trial_limit'); return 0
            prompt = Path('/app/SYSTEM_PROMPT.txt').read_text(encoding='utf-8-sig').strip()
            gemini = Gemini(env['GEMINI_API_KEY'], prompt)
            gemini.select_model()
            gemini.generate('Chỉ trả lời một câu: Kiểm tra Gemini thành công.')
            forwarder = AIForwarder(gemini, zalo, lambda: not stop.is_set(), quota.claim)
            armed = time.time()*1000
            print('CLOUD ON — Gemini checked, one poller, trial total <=3.', flush=True)
            while not stop.is_set():
                errors = []
                event = receive_one(ReadOnlyTransport(transport), seconds=35, stop_on_error=True,
                    on_status=lambda s: errors.append(s) if s.get('phase') == 'poll_error' else None)
                if errors:
                    hold(hold_file, 'poll_error'); return 1
                if stop.is_set(): break
                if event is None: continue
                text = event.get('message', {}).get('text', '')
                if not isinstance(text, str) or TRIGGER not in text: continue
                forwarder.question = text.replace(TRIGGER, '', 1).strip()
                if not forwarder.question: continue
                result = engine.handle(forwarder, event, True, armed, still_on=lambda: not stop.is_set())
                forwarder.question = ''
                print('CLOUD: %s, trial %s/3' % (result, quota.used()), flush=True)
                if result == 'uncertain_blocked' or quota.used() >= 3:
                    hold(hold_file, 'uncertain_or_trial_limit'); return 0
            return 0
        except APIError as error:
            hold(hold_file, 'api_error')
            print('CLOUD OFF — kind=%s code=%s; no retry of uncertain sends.' % (error.kind, error.code), flush=True)
            return 1
        except Exception:
            hold(hold_file, 'configuration_or_storage_error')
            print('CLOUD OFF — configuration/storage failure; details hidden.', flush=True)
            return 1
        finally: state.close()


def main():
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *args: stop.set())
    try: return run(os.environ, stop)
    except Exception:
        print('CLOUD OFF — startup/lease failed; no secret details.', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
