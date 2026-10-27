"""Live receive-only group registration. No send receipt or old history is invented."""
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import sqlite3
import sys
import time
from .official_api import APIError, OfficialAPI, Transport
from .polling_test import ReadOnlyTransport, TokenLock, receive_one, webhook_enabled
from .webhook_switch import RUNTIME, hidden, protect

PROOF = 'local_group_profile.dpapi'
SOURCE = 'official_getUpdates_fresh_nonce_v1'
RECEIPT = 'group-verified-receive-only-v1'
PENDING = 'profile-import.pending'


class ProfileError(ValueError):
    pass


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def readonly(path):
    return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True, timeout=1)


def eligible(event, bot_id, nonce, started, now):
    from .send_once import eligible as original_filter
    from .auto_reply import TRIGGER
    if not original_filter(event, bot_id, nonce):
        return False
    message = event['message']
    stamp = message.get('date')
    return (TRIGGER in message['text'] and type(stamp) in (int, float)
            and math.isfinite(stamp) and started*1000 <= stamp <= now*1000+60000
            and len(message['chat']['id']) <= 512)


def check_targets(runtime):
    from .auto_reply import GROUP_SAMPLE
    runtime = Path(runtime)
    if any((runtime/n).exists() for n in ('one_shot.db', PROOF, GROUP_SAMPLE, PENDING)):
        raise ProfileError('EXISTING_PROFILE')
    state = runtime/'ai_reply.db'
    if state.exists():
        try:
            db = readonly(state)
            try:
                if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok': raise ValueError()
                db.execute('SELECT chat_id,event_id,status FROM deliveries LIMIT 0')
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'auto_block' in tables and db.execute('SELECT 1 FROM auto_block LIMIT 1').fetchone():
                    raise ProfileError('SEND_UNCERTAIN')
            finally: db.close()
        except ProfileError: raise
        except Exception: raise ProfileError('STATE_INVALID') from None


def _load_profile(runtime, bot_id=None):
    """Bind DPAPI proof to the actual receive-only ledger, not a fake API ack."""
    runtime = Path(runtime)
    try:
        encrypted = (runtime/PROOF).read_bytes()
        if len(encrypted) > 65536: raise ValueError()
        proof_hash = hashlib.sha256(encrypted).hexdigest()
        data = json.loads(protect(encrypted, decrypt=True))
        if (not isinstance(data, dict) or data.get('version') != 1 or data.get('source') != SOURCE
                or data.get('messages_sent') is not False or data.get('history_restored') is not False
                or data.get('mention_verified') is not False
                or not isinstance(data.get('group_id'), str) or not data['group_id'].strip()
                or len(data['group_id']) > 512): raise ValueError()
        for field in ('bot_hash', 'event_hash', 'nonce_hash'):
            value = data.get(field)
            if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value): raise ValueError()
        if bot_id is not None and data['bot_hash'] != digest(bot_id): raise ValueError()
        at = data.get('verified_at')
        if type(at) not in (int, float) or not math.isfinite(at) or at <= 0: raise ValueError()
        db = readonly(runtime/'one_shot.db')
        try:
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok': raise ValueError()
            row = db.execute('SELECT bot_hash,group_hash,event_hash,proof_hash,verified_at,source '
                             'FROM group_verifications WHERE version=1').fetchone()
            expected = (data['bot_hash'], digest(data['group_id']), data['event_hash'], proof_hash, at, SOURCE)
            if row != expected: raise ValueError()
            status = db.execute('SELECT status FROM deliveries WHERE chat_id=? AND event_id=?',
                                (data['bot_hash'], RECEIPT)).fetchone()
            if status != ('verified_receive_only:'+proof_hash,): raise ValueError()
        finally: db.close()
        return data['group_id']
    except Exception:
        raise ProfileError('PROOF_INVALID') from None


def load_profile(runtime, bot_id=None):
    if (Path(runtime)/PENDING).exists(): raise ProfileError('PENDING')
    return _load_profile(runtime, bot_id)


def persist(runtime, bot_id, event, nonce, started, now=None):
    """Only call after live selection AND explicit human confirmation; never overwrite."""
    from .state import State
    from .managed_limits import ManagedResponder
    now = time.time() if now is None else now
    runtime = Path(runtime)
    check_targets(runtime)
    if not eligible(event, bot_id, nonce, started, now): raise ProfileError('EVENT_INVALID')
    message = event['message']; group_id = message['chat']['id']
    proof = {'version': 1, 'source': SOURCE, 'bot_hash': digest(bot_id),
             'group_id': group_id, 'event_hash': digest(message['message_id']),
             'nonce_hash': digest(nonce), 'verified_at': now,
             'messages_sent': False, 'history_restored': False, 'mention_verified': False}
    raw = json.dumps(proof, sort_keys=True).encode('utf-8')
    encrypted = protect(raw)
    if protect(encrypted, decrypt=True) != raw: raise ProfileError('DPAPI_FAILED')
    proof_hash = hashlib.sha256(encrypted).hexdigest()
    runtime.mkdir(parents=True, exist_ok=True)
    # Same marker already checked by START/CHECK: any interrupted write stays blocked.
    with (runtime/PENDING).open('xb') as f:
        f.write(b'Local receive-only profile initialization incomplete. Keep all files.'); f.flush()
        os.fsync(f.fileno())
    with (runtime/PROOF).open('xb') as f:
        f.write(encrypted); f.flush(); os.fsync(f.fileno())
    with (runtime/'one_shot.db').open('xb'): pass
    state = State(runtime/'one_shot.db')
    try:
        with state.db:
            state.db.execute('CREATE TABLE group_verifications(version INTEGER PRIMARY KEY CHECK(version=1), '
                             'bot_hash TEXT NOT NULL,group_hash TEXT NOT NULL,event_hash TEXT NOT NULL,'
                             'proof_hash TEXT NOT NULL,verified_at REAL NOT NULL,source TEXT NOT NULL)')
            state.db.execute('INSERT INTO group_verifications VALUES (1,?,?,?,?,?,?)',
                             (digest(bot_id), digest(group_id), proof['event_hash'], proof_hash, now, SOURCE))
            state.db.execute('INSERT INTO deliveries VALUES (?,?,?)',
                             (digest(bot_id), RECEIPT, 'verified_receive_only:'+proof_hash))
    finally: state.close()
    ai_path = runtime/'ai_reply.db'
    if not ai_path.exists():
        with ai_path.open('xb'): pass
    state = State(ai_path)
    try:
        engine = ManagedResponder(state, bot_id, group_id)
        if engine.blocked(): raise ProfileError('SEND_UNCERTAIN')
        with state.db:
            # Preserve all existing calls, counters, Google waits and dedup records.
            # Missing home history is NOT recovered: impose a conservative fresh pause.
            state.db.execute('UPDATE ai_window_state SET local_until=max(local_until,?),notified=1 WHERE bot=?',
                             (now+300, digest(bot_id)))
            state.db.execute('INSERT OR IGNORE INTO deliveries VALUES (?,?,?)',
                             (engine.group_key, proof['event_hash'], 'profile_verification_consumed'))
    finally: state.close()
    # Read back while the startup guard is still present, then release it last.
    if _load_profile(runtime, bot_id) != group_id: raise ProfileError('PROOF_INVALID')
    (runtime/PENDING).unlink()
    return group_id


def collect(transport, runtime, confirm=input, output=print, receiver=receive_one, clock=time.time):
    """All network calls pass through the existing mutation-denying wrapper."""
    check_targets(runtime)
    read = ReadOnlyTransport(transport)
    bot_id = OfficialAPI(read).getMe()
    if webhook_enabled(read): raise ProfileError('WEBHOOK_ENABLED')
    started = clock(); nonce = 'JAT-VERIFY-'+secrets.token_hex(16).upper()
    output('READY: receive-only. Bay gio trong DUNG NHOM THU, chon @bot that va gui kem ma:')
    output(nonce)
    output('Toi da 5 phut. Khong goi sendMessage; khong doi webhook. Ctrl+C de dung.')
    event = receiver(read, seconds=300, stop_on_error=True, output=output,
                     accept=lambda e: eligible(e, bot_id, nonce, started, clock()))
    if event is None: raise ProfileError('NO_MATCHING_EVENT')
    # Do not trust an injected receiver that skips its predicate.
    if not eligible(event, bot_id, nonce, started, clock()): raise ProfileError('EVENT_INVALID')
    output('RECEIVED GROUP: ma khop, nguoi gui khong phai bot, thoi gian hop le. Khong in ID/noi dung.')
    if confirm('Ban vua gui MA tren trong dung NHOM THU? Go XAC NHAN de luu; Enter de huy: ').strip() != 'XAC NHAN':
        raise ProfileError('CANCELLED')
    persist(runtime, bot_id, event, nonce, started, now=clock())
    output('PASS LOCAL PROFILE: da luu nhom xac minh qua su kien nhan. Messages sent=0; history restored=NO.')
    output('Giu nguyen vault/DB cu; ap dung nghi an toan it nhat 5 phut. Bot van OFF.')
    output('Chay CHECK_WIN7.bat. Chi sau PASS moi mo START_WIN7_PYTHON.bat va tu bat ON.')
    return 0


HINTS = {
    'EXISTING_PROFILE': 'Da co file ho so/pending. Khong ghi de; giu runtime va bao ma nay.',
    'SEND_UNCERTAIN': 'DB con khoa gui chua ro. Dung, giu DB; khong tao ho so de ne guard.',
    'STATE_INVALID': 'DB AI hien co khong hop le/bi khoa. Khong xoa DB.',
    'WEBHOOK_ENABLED': 'Webhook dang bat. Dung; khong tu xoa/doi webhook.',
    'NO_MATCHING_EVENT': 'Chua nhan event GROUP khop ma trong thoi han, hoac API loi. Chua tao ho so.',
    'EVENT_INVALID': 'Event/ma/thoi gian khong hop le. Khong tao ho so.',
    'CANCELLED': 'Ban huy. Khong tao ho so.',
    'PROOF_INVALID': 'Bang chung luu khong khop. Giu file/pending, khong bat bot.',
    'DPAPI_FAILED': 'DPAPI readback khong dat. Khong tao ho so.',
}


def main():
    from .key_vault import VAULT_LOCK
    if not sys.stdin.isatty():
        print('Mo BAT truc tiep; khong doc token tu input chuyen huong.'); return 2
    print('NHAN SU KIEN CHI DOC. Dong moi bot/poller khac; khong chay bot o nha dong thoi.')
    print('Tao ho so MOI; khong khoi phuc lich su da mat. Giu nguyen DB/vault con lai.')
    if input('De tiep tuc go TAO MOI; Enter de huy: ').strip() != 'TAO MOI': return 2
    try:
        with TokenLock(VAULT_LOCK):
            check_targets(RUNTIME)
            token = hidden('Bot Token Zalo (an, chi trong RAM): ').strip()
            if not token: return 2
            with TokenLock(token):
                return collect(Transport(token), RUNTIME)
    except KeyboardInterrupt:
        print('OFF: da dung. Giu moi file neu co pending. Khong gui tin.'); return 130
    except ProfileError as error:
        code = str(error) if str(error) in HINTS else 'PROOF_INVALID'
        print('OFF LOCAL_PROFILE ['+code+']: '+HINTS[code]); return 50
    except APIError as error:
        print('OFF LOCAL_PROFILE API kind=%s code=%s; details hidden.' % (error.kind, error.code)); return 51
    except Exception:
        print('OFF LOCAL_PROFILE: lock/DPAPI/file failure; details hidden. Giu pending/DB neu co.'); return 52
