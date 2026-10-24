# Mốc AUTO đã chạy thật — 24/10/2026

Chủ dự án xác nhận lúc khoảng 15:16 UTC+7 gửi “@Bot JAT Design xin chào” trong nhóm; bot trả lời đúng “JAT Design đã nhận tin!”.

Đối chiếu auto_reply_status.json tại máy: at_utc=2026-10-24T08:15:57.592119+00:00, outcome=sent, attempts=1, limit=5, cooldown_seconds=10, filter=exact_text_substring, entity_verified=false. Đây là API ack cộng xác nhận hiển thị từ người dùng, không chỉ unit test.

Code chạy thật ở local commit de363c34d0bafb6476153b1f3ca420991a50270c; nhánh GitHub AUTO trước mốc là jat-design/auto-mention-validation. Mốc mới stable-auto-20261024 chỉ bổ sung tài liệu, không đổi code/launcher nhận gửi.

Nhánh này là mốc khôi phục trước Gemini: START_AUTO.bat, AutoResponder, getUpdates/sendMessage, bộ lọc chuỗi, nhóm thử đã xác minh, mặc định OFF, cooldown10, max5/phiên. Không chứng nhận mention entity. Chưa Railway.

ZIP source không có runtime/credential/DB/chat; khi khôi phục phải giữ dữ liệu local đang dùng, đặc biệt one_shot.db, auto_reply.db, mẫu nhóm mã hóa. Không chạy bản sao database trống để né chống trùng hoặc trạng thái uncertain. Không đưa API key/token vào SYSTEM_PROMPT hoặc Git.
