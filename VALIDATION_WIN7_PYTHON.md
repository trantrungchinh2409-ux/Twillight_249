# Kiểm chứng bản Python Windows 7 — 26/10/2026

Base GitHub: jat-design/failover-win7-portable, 61a1a3d9884938736ee83a762e3cdf10cc570105.
Nhánh phát triển mới: jat-design/win7-python38-launchers-20261026. Không thay nhánh stable.

Đã kiểm tra dependency: runtime hoàn toàn thư viện chuẩn. Không cần pip/PyInstaller; SQLite/DPAPI lấy từ Python 3.8.10 x64 đã cài và Windows. Lỗi _sqlite3 của EXE cũ không được sửa bằng việc thay DLL; launcher bỏ qua EXE và kiểm đúng module từ Python.

Thêm launcher/check/menu/package; không sửa các module Gemini, polling, key vault, hạn mức, dedup, profile, prompt đã có. Công việc Cloudflare chưa commit được bảo toàn ở Git stash trước khi chuyển nhánh.

Kiểm thử Linux: bộ test gốc 130 có các lỗi Windows-only (DPAPI/mutex), một failure vì platform guard và một skip; không coi đó là kiểm chứng native Windows hoặc tự mock DPAPI để tuyên bố đạt. Các test đa nền tảng và test mới được chạy riêng, ghi kết quả thực trong báo cáo bàn giao. GitHub Actions mới chạy toàn bộ suite, self-test DPAPI và kiểm launcher bằng CPython 3.8.10 x64 trên windows-2022. Trạng thái job phải đọc được mới được tuyên bố Windows CI đạt; việc lưu workflow không đồng nghĩa đã chạy.

ZIP theo allowlist, có CRC/readback/SHA-256 và SOURCE_MANIFEST.json; không bao gồm runtime, token/key, DB, profile riêng, .git, EXE/DLL, node_modules hoặc .venv. Đây là source để chạy trực tiếp, không phải EXE hoặc chứng nhận tương thích Windows 7.

Chưa nghiệm thu trên máy Windows 7 SP1 thật; không có cuộc gọi Gemini/Zalo thật trong lần sửa này. Cần người dùng chạy INSTALL rồi START trên máy đích. Không thay đổi mạng, chứng chỉ, webhook hoặc dịch vụ Cloudflare đang có.

Kết quả tại môi trường Codex: suite đa nền tảng được chọn chạy 93 test, 92 passed và 1 native-Windows skipped, không lỗi. Sáu test launcher riêng: 5 passed, 1 native-Windows skipped. Đã đối chiếu diff: các module lõi được liệt kê ở trên và SYSTEM_PROMPT.txt hoàn toàn không đổi. ZIP đã kiểm CRC và SHA-256 từng thành phần; không kèm file bí mật hoặc DB. Không coi các skip Windows là passed.
