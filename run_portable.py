"""Single onedir console entry: bot, setup, profile transfer, offline checks."""
import json
from pathlib import Path
import platform
import sqlite3
import ssl
import sys
import tempfile
import urllib.error
import urllib.request

# Direct EXE launch and redirected checks must handle Vietnamese independently of BAT/codepage.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf-8', errors='replace')

BASE = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
# Set path before importing modules with user-runtime defaults; do not alter proven modules.
from jat_design import webhook_switch
webhook_switch.RUNTIME = BASE/'runtime'
from jat_design import managed_ai, setup_api, portable_profile


def self_test():
    from jat_design.webhook_switch import protect
    from jat_design.key_vault import Vault, KeyPool
    from jat_design.gemini_client import GeminiError
    from jat_design.state import State
    from jat_design.managed_limits import ManagedResponder
    from jat_design.polling_test import TokenLock
    context = ssl.create_default_context()
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        vault = Vault(folder/'probe.dpapi'); vault.add('synthetic-offline-probe')
        assert len(Vault(folder/'probe.dpapi').data['items']) == 1
        assert b'synthetic-offline-probe' not in (folder/'probe.dpapi').read_bytes()
        vault.add('synthetic-offline-backup'); key_calls = []
        class FakeGemini:
            quota = False
            def __init__(self, key, prompt): self.key = key
            def generate(self, question):
                key_calls.append(self.key)
                if self.key == 'synthetic-offline-probe':
                    raise GeminiError('synthetic invalid key', 401, 'http')
                if self.quota: raise GeminiError('synthetic quota', 429, 'http', retry_after=90)
                return 'Synthetic answer.'
        pool = KeyPool(vault, 'synthetic prompt', FakeGemini, output=lambda _: None)
        assert pool.generate('synthetic question') == 'Synthetic answer.'
        assert pool.status()['active'] == 2 and len(key_calls) == 2
        FakeGemini.quota = True
        try: pool.generate('synthetic quota check'); raise AssertionError('429 missing')
        except GeminiError as error: assert error.code == 429
        assert len(key_calls) == 3 and Vault(folder/'probe.dpapi').wait_remaining() > 80
        clock = [1800000000.0]; sent = []
        class FakePool:
            calls = 0
            def wait_remaining(self): return 0
            def generate(self, question): self.calls += 1; return 'Synthetic answer.'
        class FakeAPI:
            fail = False
            def sendMessage(self, group, text):
                sent.append(text)
                if self.fail: raise TimeoutError('synthetic timeout')
                return {'message_id': 'synthetic-ack'}
        state = State(folder/'probe.db'); fake_pool, fake_api = FakePool(), FakeAPI()
        try:
            engine = ManagedResponder(state, 'synthetic-bot', 'synthetic-group', clock=lambda: clock[0])
            def event(number):
                return {'event_name': 'message.text.received', 'message': {
                    'chat': {'id': 'synthetic-group', 'chat_type': 'GROUP'},
                    'from': {'id': 'synthetic-human', 'is_bot': False},
                    'message_id': str(number), 'text': '@Bot JAT Design synthetic', 'date': clock[0]*1000}}
            def handle(number): return engine.handle(fake_api, fake_pool, event(number), True, 1800000000000)
            for i in range(10):
                clock[0] = 1800000000+i*10
                assert handle(i) == 'sent'
            clock[0] += 10
            assert handle('notice') == 'notice_sent'
            clock[0] += 10
            assert handle('paused') == 'internal_wait' and fake_pool.calls == 10
            clock[0] = 1800000390; fake_api.fail = True
            assert handle('resumed-timeout') == 'uncertain_blocked'
            clock[0] += 10
            assert handle('never-retry') == 'uncertain_blocked' and len(sent) == 12
        finally: state.close()
        with TokenLock('JAT-portable-offline-self-test'): pass
    print(json.dumps({'offline_self_test': 'passed', 'python': platform.python_version(),
          'openssl': ssl.OPENSSL_VERSION, 'sqlite': sqlite3.sqlite_version,
          'runner_os': platform.platform(), 'win7_verified': False, 'network_calls': 0, 'failover_and_429': 'passed', 'limits_and_uncertain_send': 'passed'}))
    return 0


def check_https():
    from jat_design.official_api import NoRedirect
    # Fixed unauthenticated origins, no key/token or Zalo update consumption.
    failures = 0
    opener = urllib.request.build_opener(NoRedirect())
    for name, url in (('Google', 'https://generativelanguage.googleapis.com/'),
                      ('Zalo', 'https://bot-api.zaloplatforms.com/')):
        try:
            with opener.open(url, timeout=20) as response: code = response.status
            print('%s: HTTPS certificate validation passed, HTTP %s' % (name, code))
        except urllib.error.HTTPError as error:
            print('%s: HTTPS certificate validation passed, HTTP %s' % (name, error.code))
        except Exception:
            failures += 1; print('%s: HTTPS failed; details hidden, no security settings changed' % name)
    return 1 if failures else 0


def main():
    try:
        if sys.argv[1:] == ['--self-test']: return self_test()
        if sys.argv[1:] == ['--check-https']: return check_https()
        if sys.argv[1:] == ['--setup']:
            sys.argv = [sys.argv[0]]; return setup_api.main()
        if len(sys.argv) > 1 and sys.argv[1] in ('--export-profile', '--import-profile'):
            args = ['--export' if sys.argv[1] == '--export-profile' else '--import']+sys.argv[2:]
            return portable_profile.main(args)
        if sys.argv[1:]:
            print('Unsupported option. No bot started.'); return 2
        sys.argv = [sys.argv[0], '--prompt', str(BASE/'SYSTEM_PROMPT.txt')]
        return managed_ai.main()
    except KeyboardInterrupt:
        print('OFF — stopped; no automatic resend.'); return 130
    except Exception:
        print('OFF — startup failed; details hidden. Keep runtime and report to Codex.'); return 1


if __name__ == '__main__': raise SystemExit(main())
