"""Offline checks and launcher only; existing bot, vault and limits are unchanged."""
import argparse
import os
from pathlib import Path
import struct
import sys
import tempfile

BASE = Path(__file__).resolve().parents[1]


def compatible(version, bits, windows, win_version=None):
    if tuple(version[:3]) != (3, 8, 10) or bits != 64:
        return 'Can Python 3.8.10 x64 (khong dung Python cua EXE cu).'
    if not windows:
        return 'Can Windows 7 SP1 x64 hoac Windows moi hon de dung DPAPI.'
    if win_version is not None:
        major, minor, sp = win_version
        if (major, minor) < (6, 1) or ((major, minor) == (6, 1) and sp < 1):
            return 'Can Windows 7 Service Pack 1 hoac moi hon.'
    return None


def check(output=print):
    win = sys.getwindowsversion() if os.name == 'nt' else None
    error = compatible(sys.version_info, struct.calcsize('P')*8, os.name == 'nt',
                       (win.major, win.minor, win.service_pack_major) if win else None)
    if error:
        output(error)
        return 20
    try:
        import _sqlite3
        import sqlite3
        with tempfile.TemporaryDirectory(prefix='jat-check-', dir=str(BASE)) as folder:
            db = sqlite3.connect(str(Path(folder)/'check.db'))
            try:
                db.execute('CREATE TABLE probe (k TEXT PRIMARY KEY, v INTEGER)')
                db.execute('INSERT OR IGNORE INTO probe VALUES (?,?)', ('offline', 1))
                db.commit()
                if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('sqlite integrity')
            finally:
                db.close()
        output('OK: SQLite cua Python %s; doc/ghi database tam thanh cong.' % sqlite3.sqlite_version)
    except (ImportError, OSError, ValueError):
        output('SQLite/_sqlite3 cua Python khong tai/ghi duoc. Khong thay DLL thu cong; giu runtime cu.')
        return 21
    try:
        import ssl
        context = ssl.create_default_context()
        if context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
            raise ValueError('TLS verification required')
        from .webhook_switch import protect
        sample = b'JAT-offline-DPAPI-probe'
        if protect(protect(sample), decrypt=True) != sample:
            raise ValueError('DPAPI readback')
        from . import managed_ai, setup_api, portable_profile
        from .polling_test import TokenLock
        with TokenLock('JAT-source-offline-check'):
            pass
        prompt = (BASE/'SYSTEM_PROMPT.txt').read_text(encoding='utf-8-sig').strip()
        if not prompt or len(prompt) > 4000:
            raise ValueError('Prompt invalid')
    except Exception:
        output('DPAPI/TLS/import/cau hinh khong dat. Khong xoa runtime, khong tat TLS; bao ma 22.')
        return 22
    output('OK: Python 3.8.10 x64, DPAPI, mutex, TLS va source. Khong goi API, khong gui tin.')
    return 0


def profile(mode):
    from . import portable_profile
    if mode == '--import-profile':
        path = input('Duong dan transfer-profile-private.zip (de trong de huy): ').strip().strip('"')
        return portable_profile.main(['--import', path]) if path else 0
    source = input('Thu muc runtime cu (de trong de huy): ').strip().strip('"')
    return portable_profile.main(['--export', source, str(BASE/'runtime'/'transfer-profile-private.zip')]) if source else 0


def install_menu():
    print('Khong can pip/PyInstaller. Khong tu tai Python/DLL hay thay doi he thong.')
    print('Dung tat ca bot cu truoc khi chuyen ho so. Khong xoa database de reset gioi han.')
    while True:
        command = input('1: API Gemini | 2: Nhap ho so | 3: Xuat ho so | 4: Kiem HTTPS | Q: Xong: ').strip().upper()
        if command == 'Q':
            return 0
        if command == '1':
            from .setup_api import main as setup
            result = setup()
        elif command in ('2', '3'):
            result = profile('--import-profile' if command == '2' else '--export-profile')
        elif command == '4':
            from run_portable import check_https
            result = check_https()
        else:
            continue
        if result:
            print('Tac vu dung voi ma %s; du lieu runtime duoc giu nguyen.' % result)


def main(argv=None):
    parser = argparse.ArgumentParser(description='JAT Design: installed Python 3.8.10 x64, not EXE')
    modes = parser.add_mutually_exclusive_group()
    for option in ('check', 'install', 'setup', 'import-profile', 'export-profile', 'check-https'):
        modes.add_argument('--'+option, action='store_true')
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    try:
        result = check()
        if result or args.check:
            return result
        if not sys.stdin.isatty():
            print('Can CMD tuong tac; khong doc token/key tu input chuyen huong.')
            return 2
        if args.install:
            return install_menu()
        if args.setup:
            from .setup_api import main as setup
            return setup()
        if args.import_profile or args.export_profile:
            return profile('--import-profile' if args.import_profile else '--export-profile')
        if args.check_https:
            from run_portable import check_https
            return check_https()
        from .managed_ai import main as bot
        # Existing argument parser accepts only --prompt. No wrapper switches leak into it.
        sys.argv = [str(BASE/'run_win7_python.py'), '--prompt', str(BASE/'SYSTEM_PROMPT.txt')]
        return bot()
    except KeyboardInterrupt:
        print('OFF: da dung, khong tu gui lai.')
        return 130
    except Exception:
        print('OFF: khoi dong/tac vu khong thanh cong; giu runtime va bao Codex. Khong in secret.')
        return 1
