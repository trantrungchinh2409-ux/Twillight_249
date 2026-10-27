"""Opt-in Agent entry. The accepted run_win7_python.py remains byte-for-byte intact."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
BASE=Path(__file__).resolve().parent


def verify_base(base):
    import hashlib,json
    try:
        manifest=json.loads((base/'AGENT_BASELINE.json').read_text(encoding='utf-8'))
        for name,digest in manifest['sha256'].items():
            if hashlib.sha256((base/name).read_bytes()).hexdigest()!=digest:return False
        return True
    except Exception:return False


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser()
    g=parser.add_mutually_exclusive_group()
    g.add_argument('--names',action='store_true');g.add_argument('--check',action='store_true')
    g.add_argument('--probe-followup',action='store_true')
    g.add_argument('--self-test',action='store_true')
    args=parser.parse_args(argv)
    if not verify_base(BASE):
        print('OFF E60 AGENT_BASE_MISMATCH: copy Agent add-on into the existing accepted Win7 folder. No file changes made.');return 60
    from jat_design.win7_console import console_mode
    with console_mode():
        try:
            from jat_design.win7_python import check
            result=check()
            if result:return result
            if args.self_test:
                import unittest
                sys.path.insert(0,str(BASE/'tests'))
                suite=unittest.defaultTestLoader.loadTestsFromName('test_agent_win7')
                return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1
            if args.check:
                from jat_design.key_vault import VAULT_LOCK
                from jat_design.polling_test import TokenLock
                from jat_design.startup_check import ready
                with TokenLock(VAULT_LOCK):return ready(BASE/'runtime',BASE/'SYSTEM_PROMPT.txt')
            if args.probe_followup:
                from jat_design.agent_followup_probe import main as probe
                return probe(BASE)
            if args.names:
                from jat_design.agent_names import main as names
                return names(BASE)
            from jat_design.agent_app import main as agent
            return agent(BASE)
        except KeyboardInterrupt:
            print('OFF: stopped. No automatic resend.');return 130
        except Exception:
            print('OFF AGENT: API/lock/DPAPI/state failure; details hidden. Keep runtime and original bot.');return 1


if __name__=='__main__':raise SystemExit(main())
