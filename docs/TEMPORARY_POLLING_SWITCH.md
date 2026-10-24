# Chuyển Webhook sang polling tạm thời — 24/10/2026

Chủ dự án đã cho phép chuyển tạm sau khi báo cáo getMe chấp nhận token và getWebhookInfo cho biết webhook đang bật. Đây là kết quả do người dùng cung cấp; chưa có kết quả API chuyển thật được ghi nhận khi tạo tài liệu này.

Đã thêm công cụ SWITCH_TO_POLLING/RESTORE_WEBHOOK. Chỉ mở rộng transport cho deleteWebhook và setWebhook, giữ ReadOnlyTransport của START_TEST không có quyền mutation/gửi. Xác thực lại getMe, khóa theo token trong phiên Windows. Bản sao gồm URL, thông tin trạng thái, bot ID và khóa webhook cũ do chủ tài khoản nhập; toàn bộ mã hóa user-scoped Windows DPAPI, không lưu Bot Token. Ghi/flush/read/decrypt kiểm trước delete, kiểm cấu hình không đổi trước thao tác, không tự retry mutation. Sau delete phải getWebhookInfo.url == rỗng. Nếu timeout, trạng thái chưa xác định, không khẳng định tắt thành công.

Khóa webhook cũ cần do chủ tài khoản nhập đúng tại máy; không thể đọc lại từ getWebhookInfo hoặc Worker secret storage. Nếu chưa có, dừng trước delete. Công cụ không chứng minh secret nhập khớp Worker; không tạo secret mới, không reset Bot Token hoặc đổi secret trên Worker. Khôi phục dùng setWebhook URL+secret từ bản sao và xác nhận URL; báo riêng callback verification, không gọi thêm testWebhook. Lỗi callback 403 lịch sử có thể còn nguyên.

57/57 unittest qua trên Windows (mẫu API tổng hợp): native DPAPI roundtrip, backup trước delete, dừng khi backup lỗi hoặc webhook thay đổi, không retry delete timeout, từ chối sai bot khi restore, thiếu secret không mutation, boolean response delete theo mô tả API. START_TEST vẫn chỉ nhận, không trả lời. Unit test không chứng minh đã xóa/khôi phục webhook thật.

Nguồn đã mở: https://docs.zaloplatforms.com/docs/BOT/apis/deleteWebhook (POST, không tham số; mô tả trả true nhưng ví dụ result object URL rỗng), /getWebhookInfo (POST), /setWebhook (HTTPS URL, secret_token 8–256 ký tự). setWebhook có thể lưu URL ngay cả callback verification thất bại; cần phân biệt hai kết quả.

Không xóa Worker, không deploy Cloudflare, không reset token, không mở Railway/Gemini, không gửi tin. Chờ người dùng nhập bí mật tại máy và trạng thái live. Sau sự kiện GROUP thật mới xin phép gửi đúng một câu.
