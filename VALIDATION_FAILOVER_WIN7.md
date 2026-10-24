# Kiểm chứng API failover và ứng viên Win7 — 24/10/2026

## Đã đạt trên Windows 11

- 130/130 unittest trên Python 3.13.9 và 130/130 trên CPython 3.8.10 x64. DPAPI native, khóa giả; không dùng Gemini key thật hoặc gửi Zalo trong đợt này.
- Lỗi key invalid/revoked có fallback và CMD số thứ tự; nhớ active key qua restart, STATUS chỉ trạng thái. 429, timeout, mạng, nội dung, billing, quyền chung không đổi khóa để thử né lỗi. Billing reason ưu tiên hơn mã auth khi phân loại.
- Ngân sách 10/120 giây, pause300, thông báo một lần, cooldown10, dedup/restart và uncertain send tiếp tục được kiểm thử. managed_limits.py không đổi.
- Build thực tế onedir: CPython3.8.10 x64 chính thức (chữ ký PSF Valid), PyInstaller5.13.2, hooks2023.8, dependency ghim requirements-build.txt. Không dùng runtime Python3.13 cho EXE.
- EXE thật chạy self-test với PATH chỉ có Windows System32: DPAPI, SQLite, mutex, failover, 429, hạn mức/nghỉ, gửi timeout. Không cần Python trên PATH; không có network call trong self-test.
- EXE thật export/import hồ sơ giả: mã hóa lại DPAPI, đúng nhóm/bot, giữ counter và dedup; nhập lần hai bị từ chối. Unknown option/redirected input không khởi động bot.
- Rà PE: tất cả native EXE/DLL/PYD là x64; header OS <=6.1 là bằng chứng tĩnh, không chứng minh Win7 runtime. Ngoài bootloader EXE, mọi DLL/PYD khớp byte với phân phối PSF3.8.10. Không kèm DLL UCRT/API-set từ PATH ngoài hoặc Windows11.
- HTTPS từ EXE cuối: Google root HTTP404, Zalo root HTTP200, xác minh chứng chỉ bật; không credential, không generateContent/getUpdates/sendMessage. Chỉ chứng minh mạng/TLS trên Windows11.
- Source getUpdates/sendMessage/poller/parser, SYSTEM_PROMPT, START_AUTO/SEND_ONCE giữ nguyên nội dung. Thư mục Windows11 cũ và one_shot.db/ai_reply.db giữ nguyên SHA256. Khác CRLF/LF do Git checkout không đổi mã nguồn.

## Chưa đạt / trở ngại

Chưa có máy hoặc VM Windows7 SP1 x64 để thử. PyInstaller5.13.2 ghi hệ điều hành được hỗ trợ chính thức từ Windows8, nên bản nhắm Win7 là ứng viên, không được coi là đã tương thích. Cần nghiệm thu DLL/UCRT, DPAPI ở tài khoản Win7 đích, TLS/proxy mạng công ty, khóa màn hình, rút/cắm mạng và một câu Zalo thật. Không có bằng chứng các hạng mục này trên Win7.

Ứng viên không bundle UCRT từ Windows11. Máy Win7 phải có UCRT chính thức phù hợp do quản trị cung cấp (KB2999226 hoặc bản thay thế thích hợp). Không tự cài/đổi bảo mật. Python3.8/OpenSSL1.1.1k đã cũ, không phải runtime được hỗ trợ bảo mật hiện hành. Xem README_WIN7_VI và THIRD_PARTY_WIN7.

Nếu ứng viên không tải được trên Win7, phương án thay thế là build/verify trong máy hoặc VM Win7 SP1 x64 hợp lệ, Python3.8.10 và toolchain đã ghim; có thể cần build bootloader tại máy đích. Không thay DLL hoặc tắt TLS để ép chạy. scripts/build_win7_candidate.py và scripts/verify_portable_candidate.py được bàn giao để tái lập và đối chiếu lỗi thực tế.

Bản Win11 cũ được giữ nguyên trên jat-design/api-vault-and-limits; stable-ai-20261024 và railway-preparation không bị sửa. Không triển khai Railway hoặc kích hoạt gói phí.
