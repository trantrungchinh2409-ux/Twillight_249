"""Console V0.1 candidate; AI and GUI deliberately not included."""
import argparse
import getpass
import os
import sys
from . import __version__
from .core import Engine, REPLY
from .mock_api import MockAPI, scenario
from .official_api import APIError, OfficialAPI, Transport
from .state import State


def self_test():
    state = State(':memory:')
    try:
        api = MockAPI(scenario('jat-design-mock-id'))
        engine = Engine('jat-design-mock-id', state)
        outcomes = [engine.step(api) for _ in range(5)]
        expected = ['ignored', 'ignored', 'sent', 'duplicate', 'idle']
        if outcomes != expected or api.sent != [('group', REPLY)]:
            print('FAIL: internal mock scenario', file=sys.stderr)
            return 1
        print('PASS: internal mock only; no Zalo connection, no Windows 7 validation')
        return 0
    finally:
        state.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description='JAT Design V0.1 candidate (offline)')
    parser.add_argument('--version', action='version', version=__version__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--self-test', action='store_true')
    modes.add_argument('--mock', action='store_true')
    modes.add_argument('--live', action='store_true')
    modes.add_argument('--check-api', action='store_true')
    args = parser.parse_args(argv)
    if args.self_test or args.mock:
        return self_test()
    if args.check_api:
        try:
            token = os.environ.get('ZALO_BOT_TOKEN') or getpass.getpass('Zalo bot token (hidden): ')
            OfficialAPI(Transport(token)).getMe()
        except (APIError, ValueError, EOFError, KeyboardInterrupt):
            print('API identity check failed; details hidden. No messages sent.', file=sys.stderr)
            return 1
        print('PASS: getMe accepted token. No group or send test performed.')
        return 0
    if args.live:
        print('LIVE BLOCKED: group mention metadata not verified. See docs/API_CONTRACT.md.',
              file=sys.stderr)
        return 2
    parser.print_help()
    print('Offline candidate only. Use --mock to verify internal logic.')
    return 0
