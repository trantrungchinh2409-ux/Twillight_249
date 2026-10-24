"""Explicit private transfer of verified group + dedup/counters, never API keys."""
import argparse
import json
from pathlib import Path
import sqlite3
import tempfile
import zipfile
from .auto_reply import GROUP_SAMPLE, TRIGGER
from .key_vault import VAULT_LOCK
from .polling_test import TokenLock
from .webhook_switch import RUNTIME, protect

APPROVAL = 'approved-single-send-20261024'
FILES = {'profile.json', 'ai_reply.db', 'one_shot.db'}


def readonly(path):
    return sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro', uri=True)


def checked_profile(profile):
    if (not isinstance(profile, dict) or profile.get('version') != 1
            or not isinstance(profile.get('group_id'), str) or not profile['group_id'].strip()
            or len(profile['group_id']) > 512
            or not isinstance(profile.get('bot_hash'), str) or len(profile['bot_hash']) != 64
            or any(c not in '0123456789abcdef' for c in profile['bot_hash'])):
        raise ValueError('Invalid private profile')
    return profile


def export_profile(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists(): raise FileExistsError('Do not overwrite transfer')
    destination.parent.mkdir(parents=True, exist_ok=True)
    event = json.loads(protect((source/GROUP_SAMPLE).read_bytes(), decrypt=True))
    m = event.get('message', {}); chat = m.get('chat', {})
    if (event.get('event_name') != 'message.text.received' or chat.get('chat_type') != 'GROUP'
            or not isinstance(m.get('text'), str) or TRIGGER not in m['text']):
        raise ValueError('Invalid verified sample')
    db = readonly(source/'one_shot.db')
    try:
        rows = db.execute('SELECT chat_id,status FROM deliveries WHERE event_id=?', (APPROVAL,)).fetchall()
    finally: db.close()
    rows = [r for r in rows if r[1].startswith('api_acknowledged:')]
    if len(rows) != 1: raise ValueError('Ambiguous approval')
    profile = checked_profile({'version': 1, 'group_id': chat.get('id'), 'bot_hash': rows[0][0]})
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        db = sqlite3.connect(folder/'one_shot.db')
        try:
            db.execute('CREATE TABLE deliveries(chat_id TEXT,event_id TEXT,status TEXT,PRIMARY KEY(chat_id,event_id))')
            db.execute('INSERT INTO deliveries VALUES (?,?,?)', (rows[0][0], APPROVAL, rows[0][1])); db.commit()
        finally: db.close()
        db, copy = readonly(source/'ai_reply.db'), sqlite3.connect(folder/'ai_reply.db')
        try: db.backup(copy)
        finally: db.close(); copy.close()
        (folder/'profile.json').write_text(json.dumps(profile), encoding='utf-8')
        with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for name in sorted(FILES): archive.write(folder/name, name)
    return destination


def import_profile(archive, target=RUNTIME):
    target = Path(target); target.mkdir(parents=True, exist_ok=True)
    if any((target/n).exists() for n in ('ai_reply.db', 'one_shot.db', GROUP_SAMPLE, 'profile-import.pending')):
        raise FileExistsError('Existing state preserved; do not overwrite')
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        with zipfile.ZipFile(archive) as z:
            if len(z.infolist()) != 3 or set(z.namelist()) != FILES: raise ValueError('Wrong transfer contents')
            if sum(i.file_size for i in z.infolist()) > 16*1024*1024: raise ValueError('Transfer too large')
            for name in FILES: (folder/name).write_bytes(z.read(name))
        profile = checked_profile(json.loads((folder/'profile.json').read_text(encoding='utf-8')))
        receipt, state = readonly(folder/'one_shot.db'), readonly(folder/'ai_reply.db')
        try:
            if receipt.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Invalid DB')
            if state.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Invalid DB')
            row = receipt.execute('SELECT status FROM deliveries WHERE chat_id=? AND event_id=?',
                                  (profile['bot_hash'], APPROVAL)).fetchone()
            if not row or not row[0].startswith('api_acknowledged:'): raise ValueError('No approval')
        finally: receipt.close(); state.close()
        sample = {'event_name': 'message.text.received', 'message': {
            'chat': {'id': profile['group_id'], 'chat_type': 'GROUP'}, 'text': TRIGGER}}
        encoded = protect(json.dumps(sample).encode('utf-8'))  # Encrypt under target Windows user.
        marker = target/'profile-import.pending'
        marker.write_text('Import pending. Keep state and report to Codex if interrupted.', encoding='ascii')
        # Any interruption leaves a guard. Never overwrite or reset previous counters.
        for name in ('one_shot.db', 'ai_reply.db'):
            with (target/name).open('xb') as out: out.write((folder/name).read_bytes())
        with (target/GROUP_SAMPLE).open('xb') as out: out.write(encoded)
        marker.unlink()


def main(argv=None):
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--export', nargs=2, metavar=('SOURCE_RUNTIME', 'PRIVATE_ZIP'))
    g.add_argument('--import', dest='incoming', type=Path)
    args = p.parse_args(argv)
    print('Đóng mọi bot trước khi chuyển máy. Hồ sơ riêng chứa ID nhóm và trạng thái; không chứa API Key/token.')
    try:
        with TokenLock(VAULT_LOCK):
            if args.export: export_profile(*args.export)
            else: import_profile(args.incoming)
        print('Đã chuyển hồ sơ. Không chạy hai máy cùng lúc. Nhập lại API Key bằng SETUP_API trên máy đích.')
        return 0
    except Exception:
        print('Không chuyển được hồ sơ; giữ nguyên dữ liệu, không in thông tin riêng. Không tự xóa database.')
        return 1


if __name__ == '__main__': raise SystemExit(main())
