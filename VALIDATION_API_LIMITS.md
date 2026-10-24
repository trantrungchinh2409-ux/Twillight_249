# Xác minh bản quản lý khóa và hạn mức — 24/10/2026

- Windows thật, Python unittest: **117/117 đạt**. Không dùng khóa Gemini thật, không gọi Zalo/Google trong suite.
- DPAPI native: 12 khóa giả, phát hiện trùng, chọn chính/xóa, mở lại kho trong tiến trình Python mới; ciphertext không chứa khóa giả plaintext. Kiểm lỗi ghi giữ nguyên tệp cũ.
- Nhập nhiều khóa qua luồng Enter/Y; chỉ kiểm khóa đã chọn; lỗi xác thực có fallback, 429/billing/network/403 chung/404 không xoay khóa. Retry-After số/ngày HTTP và RetryInfo được xử lý.
- 10 lượt/120 giây, cửa sổ trượt, nghỉ 300 giây, thông báo một lần, tự tiếp tục; thay pool khóa không reset ngân sách. Giữ trạng thái nghỉ/thông báo/Google429/gửi chưa rõ khi mở DB lại.
- Cooldown, chống trùng, OFF, nhóm sai/tin riêng/tự gửi/tin thường bị bỏ qua. Timeout gửi câu thường hoặc thông báo không được tự gửi lại.
- SHA256 START_AUTO.bat, SEND_ONCE.bat, auto_reply.py, send_once.py, official_api.py, polling_test.py và runtime/one_shot.db khớp trước nâng cấp.
- START_AI mới không thực hiện request Gemini lúc khởi động; đọc kho đã lưu, OFF mặc định, không thay webhook. Chưa xác minh tương tác bàn phím bằng khóa thật hoặc tin Zalo thật với chính sách mới.
- Mã AI cũ, SYSTEM_PROMPT tối ưu, model 3.5 Flash-Lite và cấu hình sinh câu được bảo toàn. Nhánh stable và Railway không sửa; không tạo tài nguyên trả phí.

Suite được chạy lại từ ZIP đã giải nén trước bàn giao. ZIP chỉ gồm source được Git theo dõi; không runtime, database, kho DPAPI, file .env thật hoặc credential.
