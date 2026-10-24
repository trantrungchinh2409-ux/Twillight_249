"""Bounded structured local status log; no free-form provider/console text."""
from datetime import datetime, timezone
import json
from .webhook_switch import RUNTIME

EVENTS = {'start', 'poll_wait', 'result', 'key_switch'}
FIELDS = {'active', 'kind', 'code', 'seconds', 'outcome'}
KINDS = {'network', 'timeout', 'http', 'api', 'tls', 'unknown', 'invalid_json', 'redirect'}
OUTCOMES = {'sent', 'notice_sent', 'off', 'ignored', 'old_or_unknown_time', 'empty_question',
            'duplicate', 'cooldown', 'internal_wait', 'google_wait', 'uncertain_blocked',
            'invalid_key', 'billing_problem', 'provider_error'}


def record(event, folder=RUNTIME, **fields):
    if event not in EVENTS: return
    data = {'at_utc': datetime.now(timezone.utc).isoformat(), 'event': event}
    for k, v in fields.items():
        if k not in FIELDS: continue
        if k == 'kind' and (not isinstance(v, str) or v not in KINDS): continue
        if k == 'outcome' and (not isinstance(v, str) or v not in OUTCOMES): continue
        if k not in ('kind', 'outcome') and type(v) not in (int, float): continue
        data[k] = v
    try:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder/'ai_audit.jsonl'
        if path.exists() and path.stat().st_size > 1024*1024:
            path.replace(folder/'ai_audit.previous.jsonl')
        with path.open('a', encoding='utf-8') as f: f.write(json.dumps(data)+'\n')
    except OSError:
        pass  # Logging must not trigger a resend.
