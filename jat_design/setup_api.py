"""Interactive API-key setup: hidden input, explicit per-key checks only."""
from pathlib import Path
import sys
from .gemini_client import Gemini, GeminiError
from .key_vault import Vault, VAULT_LOCK, error_label
from .polling_test import TokenLock
from .webhook_switch import hidden


def show(vault, output=print):
    output('Đã lưu %s khóa DPAPI; không hiển thị nội dung khóa.' % len(vault.data['items']))
    for index, item in enumerate(vault.data['items'], 1):
        output('%s. %s — %s' % (index, 'CHÍNH' if item['id'] == vault.data['primary'] else 'DỰ PHÒNG', item['status']))
    remaining = vault.wait_remaining()
    if remaining: output('Google đang yêu cầu chờ: khoảng %s giây; không đổi khóa để né quota.' % int(remaining+1))


def add_flow(vault, read_secret=hidden, read_command=input, output=print):
    while True:
        key = read_secret('API Key tiếp theo (ẩn): ')
        try:
            added = vault.add(key)
            output('Đã lưu mã hóa.' if added else 'Khóa trùng, không lưu thêm.')
        except ValueError:
            output('Khóa trống/chứa khoảng trắng; chưa lưu.')
        show(vault, output)
        while True:
            command = read_command('Enter để thêm khóa tiếp theo; Y rồi Enter để hoàn tất: ').strip().upper()
            if command in ('', 'Y'): break
            output('Chỉ Enter hoặc Y.')
        if command == 'Y': return


def check_one(vault, index, prompt, factory=Gemini):
    if vault.wait_remaining():
        return 'quota_wait_no_request'
    item = vault.data['items'][index]
    client = factory(item['key'], prompt)
    try:
        client.select_model()
        client.generate('Chỉ trả lời một câu: Kiểm tra Gemini thành công.')
    except GeminiError as error:
        label = error_label(error); vault.mark(item, label, error.code)
        if error.code == 429: vault.quota_wait(error)
        return '%s (mã %s)' % (label, error.code)
    vault.mark(item, 'generation_verified')
    return 'generation_verified'


def main():
    print('SETUP API — lưu khóa Gemini bằng DPAPI của tài khoản Windows. Đóng START_AI trước khi sửa kho.')
    if not sys.stdin.isatty(): return 2
    try:
        with TokenLock(VAULT_LOCK):
            vault = Vault()
            if not vault.data['items']:
                add_flow(vault); return 0
            while True:
                show(vault)
                command = input('A thêm / D xóa / C kiểm tra một khóa / P chọn chính / Q thoát: ').strip().upper()
                if command == 'Q': return 0
                if command == 'A': add_flow(vault); continue
                if command not in ('D', 'C', 'P'): continue
                try:
                    index = int(input('Số thứ tự khóa: '))-1
                    if not 0 <= index < len(vault.data['items']): raise ValueError()
                except ValueError:
                    print('Số thứ tự không hợp lệ.'); continue
                if command == 'D': vault.remove(index)
                elif command == 'P': vault.primary(index)
                else:
                    print('Kiểm tra riêng khóa đã chọn: 1 request sinh câu, không kiểm hàng loạt và không gửi Zalo.')
                    prompt = 'Trả lời tiếng Việt ngắn gọn.'
                    print('Trạng thái: '+check_one(vault, index, prompt))
    except KeyboardInterrupt:
        print('\nĐã dừng; các khóa đã lưu vẫn được giữ mã hóa.'); return 130
    except Exception:
        print('Không mở/lưu được kho khóa. Đóng START_AI; kiểm tra đúng tài khoản Windows. Không in chi tiết bí mật.')
        return 1


if __name__ == '__main__': raise SystemExit(main())
