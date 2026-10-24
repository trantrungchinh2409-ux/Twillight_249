# Gửi một lần vào nhóm do chủ dự án chọn — 24/10/2026

Chủ dự án đã cho phép gửi đúng một câu: “JAT Design đã hoạt động thành công!”. Đồng thời cho phép thử gửi trực tiếp vào nhóm, ngay cả khi parser mention/reply chưa xác minh. B đã thử là reply tin thành viên, không phải reply bot; không dùng kết quả không có event đó làm bằng chứng phân biệt reply bot.

Mẫu A 14:28 xác nhận GROUP, người gửi is_bot=false, metadata message_type được lưu dạng fingerprint. Mẫu cũ chỉ giữ ID nhóm dạng alias theo từng phiên nên không thể lấy lại ID thật hoặc tự chứng minh hai mẫu cùng nhóm từ alias.

SEND_ONCE.bat tái sử dụng Transport, OfficialAPI, receive_one, TokenLock và SQLite State hiện có. Chủ dự án đóng các poller khác, nhập token ẩn. Chương trình kiểm getMe/webhook, sinh mã ngẫu nhiên mới; người dùng chọn đúng nhóm đã thử A, @bot thật và gửi kèm mã. Chỉ message.text.received/GROUP có ID hợp lệ, from.is_bot=false, sender != bot_id và chứa đúng mã độc lập mới được dùng lấy chat.id trong RAM để gửi. Không khẳng định đây là parser xác minh mention; nhóm được chủ dự án chọn bằng việc gửi mã trong nhóm đó. Không in/lưu ID hoặc nội dung tin kích hoạt.

Đặt chỗ SQLite bền trước gửi, gồm một khóa cấp quyền duy nhất theo hash bot ID và một khóa hash nhóm/event. Một lần thử cho bot trong cài đặt này; không reset/xóa runtime/one_shot.db hoặc thử bản sao khác. Lỗi gửi/ack chưa rõ không tự retry, có thể mất tin. Không hứa exactly-once. Không tự trả lời self, bot hoặc tin không đúng mã. Không sửa parser GROUP cũ hoặc bật vòng trả lời tự động.

Nếu API trả message_id, ghi one_shot_receipt.json outcome=api_acknowledged và yêu cầu người dùng nhìn thấy đúng một câu trong Zalo. API ack không thay xác nhận hiển thị. Chưa có kết quả sendMessage thật khi viết báo cáo. Không bật Gemini/Railway, không đổi webhook/token/Cloudflare.

63/63 test offline đạt trên Windows: một lần toàn cục cả event mới, khóa qua restart sau timeout, reserve trước send, reject self/bot/private/mã sai, bỏ qua event không liên quan khi polling. Fixture tổng hợp, không gọi gửi thật.

Nguồn API đã mở: https://docs.zaloplatforms.com/docs/BOT/apis/sendMessage — POST chat_id,text, kết quả message_id. Dùng adapter cũ; không build lại EXE/hệ thống.
