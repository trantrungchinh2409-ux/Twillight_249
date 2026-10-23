# JAT Design — báo cáo kiểm tra môi trường

Ngày kiểm tra: 23/10/2026. Giai đoạn: trước V0.1; chưa có bản phát hành.

## Kết quả có bằng chứng

- Kho mã `trantrungchinh2409-ux/Twillight_249`, nhánh main, HEAD `f16bfef924092fcddfcc1dcadbee1d29b231f24e`.
- Ban đầu chỉ có `index.html` của trang COUNTDOWN; không có mã Python, hướng dẫn bot, bộ kiểm thử hoặc cấu hình build.
- Git read-only qua xác thực có sẵn hoạt động (`git ls-remote origin HEAD`).
- Máy hiện tại: Linux x86_64, Python 3.12.14. Không tìm thấy Wine hoặc MinGW trong PATH. Không có máy Windows 7 được cấp trong phiên này.
- Không có biến môi trường mang tên ZALO, GEMINI hoặc OPENROUTER khi kiểm tra tên biến; không đọc hoặc ghi giá trị bí mật.
- Truy cập HTTPS các địa chỉ dưới đây bị proxy từ chối `Tunnel connection failed: 403 Forbidden`, kể cả lần thử lại sau khi lưu bản nháp miền mạng:
  - https://bot.zapps.me/docs
  - https://developers.zalo.me/docs
  - https://www.python.org/downloads/release/python-3810/

## Cấu hình đã lưu

Bản nháp thêm các miền tùy chỉnh `bot.zapps.me`, `developers.zalo.me`, `bot-api.zapps.me`, `www.python.org`; giữ nguyên preset package_managers. Đây là miền dự kiến cho việc tra cứu và kiểm tra, chưa phải bằng chứng rằng endpoint Bot API hay giao thức nhóm đã được xác nhận. Không thêm secret hoặc thay đổi danh sách kho mã.

Lưu bản nháp không tự áp dụng quyền mạng vào máy đang chạy và không xuất bản môi trường. Cần xem xét, lưu và Publish trong cài đặt môi trường, rồi thử lại các yêu cầu HTTPS.

## Thứ tự công việc tiếp theo

1. Đọc tài liệu chính thức và xác nhận endpoint long polling, xác thực, phân trang/xác nhận sự kiện, hỗ trợ nhóm, cấu trúc mention theo ID, giới hạn tốc độ và phương thức gửi trả lời. Không giả định schema giống Telegram, không dùng API Zalo cá nhân hay endpoint OA thay thế.
2. Xác định đường build Windows x64 với Python 3.8 và công cụ đóng gói tương thích Windows 7 SP1; không đổi tên binary Linux thành EXE. Có thể khảo sát Wine nhưng Wine không thay thế kiểm thử Windows 7 thật.
3. Viết V0.1 trả lời cố định chỉ với sự kiện nhóm có mention tới đúng ID bot; kiểm thử bằng fixture đúng tài liệu, rồi kiểm thử thực tế với token được nhập qua cơ chế an toàn. Không ghi token, URL có token, nội dung lỗi chứa credential vào log.
4. Build, xác nhận file PE x64 thực sự tồn tại, kiểm tra khởi động và thử bot thật. Chỉ sau cổng V0.1 mới triển khai Gemini, OpenRouter và Tkinter.
5. Bàn giao source, requirements có phiên bản cố định, script build, README tiếng Việt, EXE và ZIP; ghi riêng kết quả kiểm thử thực tế và phần chưa xác minh.

## Giới hạn hiện tại

Chưa xác minh tài liệu API, chưa cài toolchain Windows, chưa build EXE, chưa chạy bot hoặc kiểm thử Windows 7. Không có kiểm thử ứng dụng nào được chạy. Không có gói phát hành hoàn chỉnh. Không yêu cầu người dùng tự viết code. Chưa yêu cầu token vì tài liệu chính thức và đường build vẫn là các bước cần giải quyết trước.

Mỗi tác vụ cloud đã được cô lập: tiếp tục dùng checkout hiện có tại `/workspace/Twillight_249`, không tạo Git worktree trừ khi người dùng yêu cầu.
