"""User-authorized temporary webhook switch; local Windows encrypted rollback."""
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import secrets
import sys
import warnings
from urllib.parse import urlsplit
from .official_api import APIError, OfficialAPI, ProtocolError, Transport
from .polling_test import TokenLock

RUNTIME = Path(__file__).resolve().parents[1] / 'runtime'


class Blob(ctypes.Structure):
    _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_ubyte))]


def protect(data, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('Windows required for encrypted backup')
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source, target = Blob(len(data), buffer), Blob()
    function = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    function.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                         ctypes.POINTER(Blob)]
    function.restype = wintypes.BOOL
    # User-scoped DPAPI, UI forbidden; never write the plaintext secret to disk.
    if not function(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise OSError('Cannot protect/unprotect local webhook backup')
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel.LocalFree(target.pbData)


def checked_info(transport):
    result = transport.post('getWebhookInfo', {}, 15)
    if not isinstance(result, dict) or not isinstance(result.get('url'), str):
        raise ProtocolError('Unknown webhook state; no mutation allowed')
    return result


def valid_url(url):
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and bool(parsed.hostname) and
            parsed.username is None and parsed.password is None and not parsed.fragment)


def write_status(path, phase):
    # Status only, never URL, token, IDs, API description or webhook secret.
    path.with_suffix('.status.json').write_text(json.dumps({
        'phase': phase, 'at_utc': datetime.now(timezone.utc).isoformat(),
        'cloudflare_modified': False, 'messages_sent': False}), encoding='utf-8')


def disable(transport, bot_id, secret, folder=RUNTIME):
    info = checked_info(transport)
    if info['url'] == '':
        return None
    if not valid_url(info['url']) or not 8 <= len(secret) <= 256:
        raise ValueError('Valid original HTTPS URL and old webhook secret required')
    folder.mkdir(exist_ok=True, parents=True)
    path = folder / ('webhook_backup_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+
                     '_'+secrets.token_hex(4)+'.bin')
    backup = {'bot_id': bot_id, 'info': info, 'secret_token': secret,
              'created_at_utc': datetime.now(timezone.utc).isoformat()}
    raw = json.dumps(backup, ensure_ascii=False).encode('utf-8')
    encrypted = protect(raw)
    with path.open('xb') as stream:
        stream.write(encrypted)
        stream.flush()
        os.fsync(stream.fileno())
    # Verify disk read + decrypt before any remote change.
    if protect(path.read_bytes(), decrypt=True) != raw:
        raise OSError('Backup readback failed; webhook unchanged')
    write_status(path, 'backup_verified')
    # Avoid overwriting a concurrent configuration change.
    current = checked_info(transport)
    if current != info:
        raise ProtocolError('Webhook changed during preparation; delete cancelled')
    write_status(path, 'delete_attempted')
    # Do not retry a mutation after timeout; read status in a subsequent run.
    transport.post('deleteWebhook', {}, 15)
    after = checked_info(transport)
    if after['url'] != '':
        write_status(path, 'disabled_not_confirmed')
        raise ProtocolError('Deletion not confirmed by getWebhookInfo')
    write_status(path, 'disabled_confirmed')
    return path


def restore(transport, bot_id, path):
    backup = json.loads(protect(path.read_bytes(), decrypt=True).decode('utf-8'))
    if backup.get('bot_id') != bot_id:
        raise ValueError('Backup belongs to another bot')
    info, secret = backup['info'], backup['secret_token']
    if not valid_url(info['url']) or not isinstance(secret, str) or not 8 <= len(secret) <= 256:
        raise ValueError('Backup invalid')
    current = checked_info(transport)
    if current['url'] == info['url']:
        # Same URL does not prove the same secret; do not mutate it automatically.
        return 'already_configured_unverified'
    if current['url']:
        raise ProtocolError('Different webhook is active; restore cancelled')
    write_status(path, 'restore_attempted')
    result = transport.post('setWebhook', {'url': info['url'], 'secret_token': secret}, 30)
    if checked_info(transport)['url'] != info['url']:
        raise ProtocolError('Restore URL not confirmed')
    verified = (isinstance(result, dict) and isinstance(result.get('verification'), dict)
                and result['verification'].get('ok') is True)
    phase = 'restored_callback_verified' if verified else 'restored_url_callback_unverified'
    write_status(path, phase)
    return phase


def hidden(prompt):
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        return getpass.getpass(prompt)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    restoring = args == ['--restore']
    if args not in ([], ['--restore']) or not sys.stdin.isatty():
        print('Mở SWITCH_TO_POLLING.bat hoặc RESTORE_WEBHOOK.bat trực tiếp.')
        return 2
    print('Chỉ thay cấu hình Webhook Zalo. Không reset token, sửa Worker hoặc gửi tin.')
    try:
        token = hidden('Bot Token (ẩn): ').strip()
        with TokenLock(token):
            transport = Transport(token)
            bot_id = OfficialAPI(transport).getMe()
            if restoring:
                files = sorted(RUNTIME.glob('webhook_backup_*.bin'), reverse=True)
                if not files:
                    print('Chưa có bản sao webhook trên máy này.')
                    return 2
                print('Đóng mọi START_TEST trước. Bản sao gần nhất: '+files[0].name)
                if input('Gõ KHOI PHUC để khôi phục URL và secret cũ: ').strip() != 'KHOI PHUC':
                    return 2
                phase = restore(transport, bot_id, files[0])
                print('Kết quả: '+phase)
                print('URL khớp chưa chứng minh callback hoạt động; lỗi 403 cũ có thể còn.')
                return 0
            info = checked_info(transport)
            if info['url'] == '':
                print('WEBHOOK ĐÃ TẮT (getWebhookInfo xác nhận). Mở START_TEST.bat.')
                return 0
            print('Webhook đang bật. Cần khóa xác thực webhook CŨ để có thể khôi phục.')
            print('Đây là ZALO_WEBHOOK_SECRET đã dùng với Worker, KHÔNG phải Bot Token.')
            print('Phải nhập đúng khóa cũ; công cụ không đọc/đối chiếu được secret trên Worker.')
            print('Nếu không còn khóa cũ, nhấn Enter trống: dừng trước khi xóa webhook.')
            secret = hidden('Khóa webhook cũ (ẩn, mã hóa bằng tài khoản Windows hiện tại): ')
            if not 8 <= len(secret) <= 256:
                print('Chưa có khóa hợp lệ. Webhook giữ nguyên. Không đoán hoặc tạo khóa mới.')
                return 2
            path = disable(transport, bot_id, secret)
            print('WEBHOOK ĐÃ TẮT — getWebhookInfo xác nhận URL rỗng.')
            if path:
                print('Đã lưu và đọc kiểm lại bản sao mã hóa: '+path.name)
            print('Bây giờ mở START_TEST.bat, nhập token, chọn A rồi @bot thật trong nhóm.')
            return 0
    except KeyboardInterrupt:
        print('\nĐã dừng. Nếu đã gọi deleteWebhook, mở lại để đọc trạng thái; không tự retry mutation.')
        return 130
    except (APIError, OSError, ValueError, KeyError, RuntimeError, EOFError, getpass.GetPassWarning):
        print('Chưa xác nhận hoàn tất. Chi tiết nhạy cảm đã ẩn. Không tự thử lại thao tác thay đổi.')
        print('Bản sao nếu đã tạo nằm ở runtime/webhook_backup_*.bin; không gửi thư mục này lên chat/Git.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
