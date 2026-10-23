# Báo cáo bản thử Windows 11 — 24/10/2026

## Đã thực hiện

- Đọc gói bàn giao và kiểm SHA-256 của đủ 45 file nguồn theo manifest: không sai khác. Clone đúng repo/nhánh, HEAD gốc `05728a1cdafccaa0f3371b0627fb4268f13b6cd2`.
- Môi trường thực: `Windows-11-10.0.26300-SP0`, Python 3.13.9. WMI/CIM bị giới hạn quyền; thông tin hệ điều hành lấy qua Python platform, không suy từ báo cáo cũ.
- Kế thừa Transport/OfficialAPI Python; bổ sung getWebhookInfo và mã lỗi dạng số không lộ description/URL. Không sửa parser GROUP cũ để né guard.
- Có START_TEST.bat, kiểm tra Python + SSL/SQLite/ctypes. Không cần dependency bên ngoài. Token nhập ẩn và không lưu; đầu vào redirect bị từ chối để tránh token hiện ra.
- Vòng getUpdates chỉ nhận một event trong khoảng 5 phút, timeout HTTP 40 giây cho long poll 30 giây; tối đa 3 lỗi liên tiếp, backoff, Ctrl+C dừng. Bản thử không có đường gọi sendMessage/deleteWebhook/setWebhook/testWebhook.
- Khóa mutex Windows theo token ngăn bản thử thứ hai trong cùng phiên đăng nhập; không thay thế khóa toàn hệ thống nhiều máy.
- Mẫu chỉ lưu schema đã che và nhãn người thử, không raw text, token, tên hoặc ID thật. Gửi luôn OFF, GROUP parser tiếp tục fail-closed.
- **49/49 unittest đạt**, không skip trên Windows; self-test engine cũ đạt. Bao gồm khóa Windows thật, chặn poll khi webhook bật, che dữ liệu, giới hạn retry và từ chối mutation. Fixture mới đều tổng hợp và không được coi là sự kiện Zalo thật.
- Kiểm launcher qua cmd phát hiện cp1252 không in được tiếng Việt khi redirect: đặt PYTHONUTF8/PYTHONIOENCODING trong launcher, kiểm lại đường chạy đó. Đây không phải lỗi kết nối Zalo.
- Giữ nguyên Cloudflare, không deploy, không testWebhook, không đổi token hay cấu hình production. Không thêm Gemini/Railway.

## Lịch sử 403 và chênh lệch nguồn

Báo cáo cloud trong gói nói testWebhook outer API 200 nhưng callback webhook.http.403, D1 không có callback xác thực; chưa biết nguồn 403. Access chưa bật không đồng nghĩa thiếu quyền Access. Không quy riêng User-Agent, không tắt WAF/TLS/secret để né. Source chẩn đoán cloud mới hơn snapshot GitHub hiện có; không triển khai ngược snapshot này lên cloud.

Tệp `docs/zalo-bot-error-code.user.md` lịch sử có nội dung OA/refresh token; không dùng nội dung đó để tự refresh Bot Token. Bản mới dựa trên Bot API chính thức và không thay token.

## Chưa hoàn thành và cổng cần người dùng

Chưa nhập token thật, chưa gọi getMe/getWebhookInfo thật trong phiên này, chưa nhận event nhóm thật, chưa xác minh mention so với reply/mention khác, chưa gửi câu trả lời. Chưa build EXE hoặc kiểm thử trực quan cửa sổ nhập token bằng thao tác người dùng. START_TEST.bat là launcher Python, không phải EXE mới.

Chủ dự án chạy START_TEST.bat và nhập token tại máy. Nếu báo webhook đang bật, cần chủ dự án duyệt chuyển tạm sang polling; chuẩn bị khôi phục URL + secret qua cơ chế an toàn trước khi xóa cấu hình. Bản này cố ý không chứa chức năng đổi webhook. Không cam kết tự khôi phục secret từ getWebhookInfo (API không trả secret).

Sau event nhóm thật, đọc mẫu che dữ liệu, kiểm A/B/C và schema đích bot; mới viết parser và chuẩn bị một lần trả lời “JAT Design đã kết nối thành công” để chủ dự án duyệt. Railway chỉ sau nghiệm thu local; Gemini chỉ sau bot nhận/trả lời thật. Chưa phát sinh dịch vụ trả phí.

Đóng gói bằng script allowlist toàn source Python/Worker/test/tài liệu; không lấy .git, runtime, DB, credential hay cache. Kết quả CRC, hash ZIP và test sau giải nén ghi trong outputs/VERIFY_WINDOWS11.json tại thư mục bàn giao (không dùng báo cáo lịch sử thay kiểm tra mới).
