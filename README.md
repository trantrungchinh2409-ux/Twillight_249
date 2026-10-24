# Bản hiện hành — API failover và ứng viên EXE Win7

Bản portable Win7 chưa được nghiệm thu trên Win7 thật: xem [README_WIN7_VI.md](README_WIN7_VI.md). Nhánh nâng cấp jat-design/failover-win7-portable; nhánh API-vault cũ đã được chủ dự án xác nhận chạy thật, được giữ nguyên.

Xem [hướng dẫn khóa API và hạn mức](README_API_LIMITS_VI.md). Mốc AI cũ đã chạy thật; bản nâng cấp dùng DPAPI và hạn mức bền 10 lượt/2 phút. Phần bên dưới là tài liệu V0.1 lịch sử, không phải hướng dẫn START_AI hiện tại.

---

# JAT Design — Zalo Bot V0.1 (ứng viên offline)

Tiếp tục trong kho `Twillight_249`; giữ nguyên `index.html` và báo cáo thiết lập cũ. **Chưa phải bản bot hoạt động với Zalo thật. Chưa có chứng nhận tương thích Windows 7.** Chưa phát triển Gemini, OpenRouter hay Tkinter.

## Đã có

- Source Python dùng thư viện chuẩn, viết theo cú pháp Python 3.8.
- Logic chỉ gửi câu trả lời cố định trong nhóm khi metadata mention chứa đúng ID bot; chuỗi `@Bot JAT Design` trong text không đủ điều kiện.
- Bỏ qua tin riêng, bot tự gửi, bot khác, dữ liệu nội bộ sai/thiếu; lưu trạng thái SQLite chống trùng qua lần khởi động lại.
- Mock API nội bộ, bộ kiểm thử, self-test đóng gói; adapter HTTP chính thức cho getMe/getUpdates/sendMessage; chế độ live thoát mã 2 vì chưa xác minh field mention trong nhóm.
- Script Windows tự chuẩn bị Python 3.8.10 x64 nếu chưa được chỉ định, tạo venv và cài dependency build. Kiểm tra TLS và chữ ký trình cài Python được giữ nguyên.
- GitHub Actions Windows runner build và chạy EXE thật trước khi tải artifact. Workflow không dùng token Zalo hoặc secret API.

## Sử dụng bản ứng viên

Với EXE artifact do workflow build thành công: chạy `JAT-Design-0.1.0-dev.exe --self-test` hoặc `--mock`. Chạy không tham số hiển thị hướng dẫn. Đây chỉ là kiểm tra offline; chương trình chưa lắng nghe nhóm Zalo.

Lệnh cho phát triển/CI (không yêu cầu người dùng tự code):

```text
python -m unittest discover -s tests -v
python run_bot.py --self-test
python run_bot.py --live
python scripts/package_source.py
```

`--live` hiện bị khóa có chủ đích. Đã xác minh schema request và mẫu sự kiện PRIVATE, nhưng chưa có field mention nhóm được xác minh. Xem `docs/API_CONTRACT.md`. Không nhập token vào dòng lệnh, source, issue hoặc log; bản offline không cần token. `--check-api` chỉ gọi getMe để kiểm tra token, đọc biến ZALO_BOT_TOKEN hoặc nhập ẩn qua getpass; không poll hoặc gửi tin. Chưa chạy lệnh này với token thật.

## Build Windows tự động

Workflow `.github/workflows/build-windows.yml` chạy khi push/PR có thay đổi code/build, hoặc `workflow_dispatch`. Runner `windows-2022`, Python **3.8.10 x64**, dependency build được cố định trong `requirements-build.txt`. Workflow đã được đẩy lên nhánh `jat-design/v0.1-build-first`; run Windows đầu tiên: https://github.com/trantrungchinh2409-ux/Twillight_249/actions/runs/39902319964. Run này đã thành công, EXE có trong artifact Windows candidate. Xem báo cáo để biết giới hạn tải artifact và phần Zalo live còn thiếu.

Script `scripts/build_windows.ps1` tự xử lý dependency, chạy test, PyInstaller, xác minh PE32+ x64, chạy chính EXE với `--self-test` và kiểm tra `--live` vẫn bị khóa. Khi lỗi, script dừng và workflow không tải gói như một bản thành công. Cách gọi kỹ thuật: `powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1`. ExecutionPolicy chỉ áp dụng phiên shell này; không tắt TLS hoặc kiểm tra chữ ký installer.

Nếu dùng script tại máy đích, bootstrap có thể cần quyền cài Python cho người dùng và các bản cập nhật Windows/.NET/chứng chỉ cần thiết. Bootstrap chưa được kiểm thử trên Windows 7. Script không chủ động sửa registry ngoài các thay đổi của trình cài Python, cài bản cập nhật hệ điều hành hoặc bỏ qua xác minh chữ ký. Mục tiêu ưu tiên là build trên runner để máy sử dụng EXE không phải cài dependency thủ công.

Artifact thành công gồm EXE console, báo cáo xác minh EXE JSON, ZIP source và SHA-256 ZIP. Không phải binary Linux đổi đuôi. EXE ứng viên được tạo từ chế độ offline; build thành công không hoàn thành cổng Zalo live.

## Giới hạn xử lý trùng

Engine reserve trạng thái trước khi gửi, theo cách tối đa một lần cho mỗi `(chat_id, event_id)`. Nếu timeout hoặc crash khi gửi, trạng thái không được tự phát lại: có thể mất phản hồi, nhưng tránh tự gửi trùng. SQLite chỉ lưu ID và trạng thái, không lưu token hoặc nội dung. Lỗi lưu reserve ngăn gửi. Adapter thật còn phải xử lý acknowledgement và giao lại sự kiện theo tài liệu chính thức; không khẳng định exactly-once. Dữ liệu dedup cần chính sách giữ lại khi triển khai live.

## Nghiệm thu còn thiếu

1. Xác minh metadata mention nhóm để phân biệt với trả lời trích dẫn; sau đó nối adapter HTTP đã có vào vòng long polling có dừng/backoff. Request getUpdates và sendMessage đã viết, chưa có vòng bot chạy live.
2. Kiểm thử bot thật trong nhóm với token được cấp an toàn.
3. Chạy workflow Windows, lấy EXE và báo cáo xác minh hiện vật.
4. Thử EXE trên **Windows 7 SP1 64-bit thật**. Python 3.8/PyInstaller được chọn là mục tiêu kỹ thuật, không phải bằng chứng tương thích. Runner Windows Server không thay thế Windows 7.

Chỉ sau khi V0.1 đạt các cổng mới phát triển AI và giao diện. Xem `docs/V0_1_TEST_REPORT.md` để biết kết quả đã chạy, chưa chạy và blocker.
