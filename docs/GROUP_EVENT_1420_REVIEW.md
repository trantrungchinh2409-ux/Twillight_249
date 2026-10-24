# Kết quả đọc mẫu GROUP 24/10/2026 14:20:44 UTC+7

Đọc runtime/event_20261024T072044_be0c1c.json: official_getUpdates_live, message.text.received, chat_type GROUP, from.is_bot false. Chủ dự án gán nhãn mention_bot. Đây là bằng chứng nhận GROUP, chưa chứng minh parser biết mention.

Không có metadata mention đủ đọc trong mẫu đã che: một trường chuỗi bị đổi thành unknown_field_4 và giá trị <string>. Không suy ra trường này là message_type hoặc giá trị MENTION. Không thể khôi phục tên/giá trị từ file đã che. Bộ che dữ liệu cũ làm mất thông tin cần đối chiếu; đã sửa tối thiểu để giữ tên message_type/event_type/interaction_type/trigger_type, các enum đóng, giá trị khác chỉ giữ fingerprint SHA-256 để so sánh giữa các phiên. Không lưu raw chat hoặc credential.

Chưa sửa parser GROUP, chưa nối gửi chỉ dựa vào text tên bot hoặc nhãn người thử. Cần mẫu A @bot thật và B reply không @; thêm C mention người khác nếu Zalo chuyển sự kiện đó. Không có sự kiện C không chứng minh parser đã phân biệt C. Nếu field xác định được vẫn không chứng minh bot đích, cần kiểm thêm metadata ID hoặc bằng chứng hợp đồng nền tảng.

Chủ dự án đã duyệt một câu duy nhất: “JAT Design đã hoạt động thành công!”. Quyền này được giữ, không hỏi lại. Chế độ một lần gửi sẽ reserve bền trước send, bỏ qua self/bot và không retry kết quả gửi chưa rõ; chưa mở khi metadata chưa xác minh. Không thêm Gemini/Railway, không đổi webhook hoặc token.
