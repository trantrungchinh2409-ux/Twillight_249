"""Offline startup readiness and closed, secret-free initialization errors."""
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from .auto_reply import GROUP_SAMPLE, TRIGGER, hashed
from .key_vault import Vault
from .webhook_switch import protect

# Stable categories: exception messages, file paths, IDs and SQL values never enter reports.
ERRORS = {
 'PROMPT': (30, 'SYSTEM_PROMPT khong doc duoc hoac khong hop le; giu prompt cu va kiem tra file.'),
 'VAULT_MISSING': (31, 'Chua co khoa Gemini. Mo SETUP_API.bat tren chinh may/tai khoan nay.'),
 'VAULT_READ': (32, 'Khong doc/giai ma duoc kho Gemini: kiem tra tai khoan Windows va quyen file. Khong xoa kho cu.'),
 'PROFILE_DB_MISSING': (33, 'Thieu one_shot.db. Mo VERIFY_GROUP_WIN7.bat de xac minh nhom truc tiep, hoac INIT_PROFILE_WIN7.bat de nhap ho so cu.'),
 'PROFILE_DB_READ': (34, 'DB bien nhan hong/bi khoa/khong doc duoc; giu DB va chuyen day du ho so, khong tao DB rong.'),
 'PROFILE_RECEIPT': (35, 'Khong co bien nhan bot da gui thanh cong; nhap dung ho so da xac minh, khong bo qua guard.'),
 'PROFILE_SAMPLE_MISSING': (36, 'Thieu mau nhom da xac minh; nhap ho so bang INIT_PROFILE_WIN7.bat.'),
 'PROFILE_DECRYPT': (37, 'Khong giai ma/doc duoc mau nhom; file co the hong hoac khac may/tai khoan. Dung cong cu chuyen ho so.'),
 'PROFILE_INVALID': (38, 'Ho so nhom khong hop le hoac khong khop bot; nhap lai dung ho so, khong tu nhap group ID.'),
 'RUNTIME_WRITE': (39, 'Khong ghi duoc thu muc runtime. Giai nen vao thu muc co quyen ghi; khong sua bao mat Windows.'),
 'IMPORT_PENDING': (40, 'Nhap ho so chua hoan tat. Giu nguyen runtime va bao Codex, khong xoa DB hoac marker.'),
 'VAULT_LOCK': (41, 'Khong lay duoc khoa kho. Dong SETUP_API va phien AI khac; khong xoa du lieu.'),
 'BOT_LOCK': (42, 'Khong lay duoc khoa tien trinh bot. Dong poller cung token trong phien Windows nay.'),
 'STATE_MISSING': (43, 'Thieu ai_reply.db chua bo dem/chong trung. Nhap day du ho so; khong tao DB moi de reset.'),
 'STATE_READ': (44, 'DB AI hong/bi khoa/sai schema. Giu DB va bao Codex; khong reset han muc.'),
 'SEND_UNCERTAIN': (45, 'Co lan gui chua ro ket qua. Dung va giu DB; khong tu gui lai.'),
 'STARTUP_UNKNOWN': (46, 'Loi khoi tao chua phan loai. Gui ma/stage trong CMD; khong gui key/token/runtime.'),
 'TOKEN_INPUT': (47, 'Khong doc duoc token an; mo CMD truc tiep. Khong gui token vao chat.'),
 'ZALO_INIT': (48, 'Loi khoi tao ket noi Zalo; kiem tra CA G3 va ma API rieng. Khong tat TLS.'),
 'STATE_INIT': (49, 'Khong khoi tao duoc DB AI; kiem tra quyen/DB bi khoa. Giu nguyen DB.'),
}


class StartupError(Exception):
    def __init__(self, category):
        self.category = category if category in ERRORS else 'STARTUP_UNKNOWN'
        self.code, self.hint = ERRORS[self.category]
        super().__init__(self.category)


def emit(category, output=print, error=None, stage=None):
    issue = StartupError(category)
    # Only a closed class label, never str(error), traceback locals or request URL.
    kind = 'permission' if isinstance(error, PermissionError) else 'sqlite' if isinstance(error, sqlite3.Error) else 'file' if isinstance(error, OSError) else 'other'
    stage = stage if stage in ERRORS else issue.category
    output('OFF E%s [%s] stage=%s kind=%s: %s' % (issue.code, issue.category, stage, kind, issue.hint))
    return issue.code


def _db(path, category, query, parameters=()):
    try:
        db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=1)
        try:
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok': raise ValueError()
            return db.execute(query, parameters).fetchall()
        finally: db.close()
    except Exception:
        raise StartupError(category) from None


def profile(runtime, bot_id=None):
    runtime = Path(runtime)
    if (runtime/'profile-import.pending').exists(): raise StartupError('IMPORT_PENDING')
    receipt = runtime/'one_shot.db'
    if not receipt.is_file(): raise StartupError('PROFILE_DB_MISSING')
    from .local_group_profile import PROOF, load_profile
    if (runtime/PROOF).exists():
        try: group_id = load_profile(runtime, bot_id)
        except Exception: raise StartupError('PROFILE_INVALID') from None
    else:
        rows = _db(receipt, 'PROFILE_DB_READ', 'SELECT chat_id,status FROM deliveries WHERE event_id=?',
                   ('approved-single-send-20261024',))
        approved = [r for r in rows if isinstance(r[1], str) and r[1].startswith('api_acknowledged:')]
        if not approved: raise StartupError('PROFILE_RECEIPT')
        if bot_id is not None and not any(r[0] == hashed(bot_id) for r in approved):
            raise StartupError('PROFILE_INVALID')
        sample = runtime/GROUP_SAMPLE
        if not sample.is_file(): raise StartupError('PROFILE_SAMPLE_MISSING')
        try: event = json.loads(protect(sample.read_bytes(), decrypt=True))
        except Exception: raise StartupError('PROFILE_DECRYPT') from None
        m = event.get('message', {}) if isinstance(event, dict) else {}
        chat = m.get('chat', {}) if isinstance(m, dict) else {}
        if (not isinstance(event, dict) or event.get('event_name') != 'message.text.received'
                or not isinstance(chat, dict) or chat.get('chat_type') != 'GROUP'
                or not isinstance(chat.get('id'), str) or not chat['id'].strip()
                or not isinstance(m.get('text'), str) or TRIGGER not in m['text']):
            raise StartupError('PROFILE_INVALID')
        group_id = chat['id']
    state = runtime/'ai_reply.db'
    if not state.is_file(): raise StartupError('STATE_MISSING')
    _db(state, 'STATE_READ', 'SELECT chat_id,event_id,status FROM deliveries LIMIT 0')
    tables = _db(state, 'STATE_READ', "SELECT name FROM sqlite_master WHERE type='table'")
    if ('auto_block',) in tables:
        blocks = _db(state, 'STATE_READ', 'SELECT k FROM auto_block')
        if any(bot_id is None or r[0] == hashed(bot_id) for r in blocks):
            raise StartupError('SEND_UNCERTAIN')
    return group_id


def ready(runtime, prompt, require_vault=True, output=print):
    """No API, no user DB writes. Report independent missing components together."""
    runtime = Path(runtime); issues = []
    try:
        text = Path(prompt).read_text(encoding='utf-8-sig').strip()
        if not text or len(text) > 4000: raise ValueError()
        output('PASS CONFIG: SYSTEM_PROMPT.')
    except Exception: issues.append('PROMPT')
    try:
        profile(runtime)
        output('PASS PROFILE/DB: ho so xac minh, bang chung DPAPI, DB AI va guard. Bot/token se doi chieu khi khoi dong.')
    except StartupError as error: issues.append(error.category)
    except Exception: issues.append('PROFILE_DB_READ')
    if require_vault:
        if not (runtime/'gemini_keys.dpapi').is_file(): issues.append('VAULT_MISSING')
        else:
            try:
                vault = Vault(runtime/'gemini_keys.dpapi')
                if not vault.data['items']: issues.append('VAULT_MISSING')
                else: output('PASS VAULT: giai ma duoc %s khoa; chua goi Gemini de xac minh quyen.' % len(vault.data['items']))
            except Exception: issues.append('VAULT_READ')
    if runtime.exists():
        try:
            # Real write permission probe, never a user DB or key file.
            fd, path = tempfile.mkstemp(prefix='.jat-write-check-', dir=str(runtime))
            try:
                with os.fdopen(fd, 'wb') as f: f.write(b'probe'); f.flush(); os.fsync(f.fileno())
            finally: Path(path).unlink()
        except Exception: issues.append('RUNTIME_WRITE')
    for category in issues: emit(category, output)
    if issues: return StartupError(issues[0]).code
    output('PASS READY: ho so/kho hop le offline; chua chung minh API hay tin Zalo that.')
    return 0


def self_test(output=print):
    """Synthetic readiness fixture only. Never creates a real approved profile."""
    from .state import State
    with tempfile.TemporaryDirectory(prefix='jat-startup-selftest-') as temp:
        folder = Path(temp); runtime = folder/'runtime'; runtime.mkdir()
        prompt = folder/'SYSTEM_PROMPT.txt'; prompt.write_text('Synthetic prompt.', encoding='utf-8')
        vault = Vault(runtime/'gemini_keys.dpapi'); vault.add('synthetic-offline-key-not-valid')
        state = State(runtime/'one_shot.db')
        try:
            state.reserve(hashed('synthetic-bot'), 'approved-single-send-20261024')
            state.mark(hashed('synthetic-bot'), 'approved-single-send-20261024', 'api_acknowledged:synthetic')
        finally: state.close()
        state = State(runtime/'ai_reply.db'); state.close()
        sample = {'event_name': 'message.text.received', 'message': {'text': TRIGGER,
                  'chat': {'id': 'synthetic-group', 'chat_type': 'GROUP'}}}
        (runtime/GROUP_SAMPLE).write_bytes(protect(json.dumps(sample).encode()))
        if ready(runtime, prompt, output=output): return 1
        assert profile(runtime, 'synthetic-bot') == 'synthetic-group'
        output('PASS SELFTEST: du lieu gia, khong tao ho so that, khong goi API, khong gui tin.')
    return 0
