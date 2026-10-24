# Đối chiếu A/B thật — 24/10/2026

A: event_20261024T072817_ea9cb8.json, @bot thật. B: event_20261024T075612_01d92d.json, reply đúng tin bot không @. Cả hai message.text.received/GROUP, from.is_bot=false; message_type fingerprint giống hệt: 8e91df364ba7fa84d086a84a6a03d1cef712105dedc34b7423e67af89239eb04.

Không có danh sách mentions/target bot ID hoặc field reply riêng trong hai schema đã lưu. ID nhóm/người/tin dùng salt riêng mỗi phiên nên không thể so sánh alias giữa mẫu. Không dùng message_type làm discriminator. Text đã bị che, không thể khôi phục từ file; chưa đủ để biết text có markup xác thực mention hay chỉ có chuỗi tên hiển thị.

Chế độ tự động vẫn OFF, parser GROUP cũ giữ fail-closed. Không làm giả test fixture mention_verified hoặc trả lời mọi GROUP. Mốc stable-live-20261024 và code getUpdates/sendMessage giữ nguyên.

Đã chuẩn bị collector A/B cùng một token/session bằng vòng getUpdates hiện có, transport chỉ đọc. Full event mã hóa Windows DPAPI local trong runtime (.gitignore); bản JSON chia sẻ chỉ schema/feature boolean, không text/ID thật/token. Thu lại A/B để kiểm text mà không mất bằng chứng; dùng nội dung thử không riêng tư. Không gửi tin hoặc deploy server. Collector không phải auto responder.

Blocker để chuyển sang auto: phải tìm được điều kiện @bot tách khỏi reply và gõ tên thường. Nếu wire API chỉ có text tên hiển thị, không thể bảo đảm @bot thật; cần nói rõ giới hạn và chủ dự án quyết định trước khi chọn heuristic. Không tự hạ yêu cầu. ON/OFF, cooldown và dedup được chuẩn bị trong AUTO_REPLY_NEXT.md, chưa coi là tính năng tự động đã nghiệm thu. Railway/Gemini vẫn hoãn.
