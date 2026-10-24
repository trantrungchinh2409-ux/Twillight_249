# JAT Design AI — thử tối đa 3 phản hồi thật

Mốc AUTO đã thành công được giữ trên nhánh `jat-design/stable-auto-20261024` và ZIP dự phòng. START_AUTO/AutoResponder/Transport/getUpdates/sendMessage không đổi. START_AI ghép một adapter Gemini trước lời gọi gửi có sẵn; không viết lại bot.

## Chạy

1. Đóng START_AUTO và mọi poller khác.
2. Nếu muốn, sửa SYSTEM_PROMPT.txt cạnh START_AI.bat. Không đặt khóa/token vào prompt. File đọc lúc mở chương trình, không tự đọc lại giữa phiên.
3. Mở TEST_GEMINI.bat để chỉ kiểm model và một câu Gemini, không cần token Zalo. Hoặc mở START_AI.bat: nó tự thực hiện bước kiểm thử Gemini trước.
4. Nhập Gemini API key ẩn. Chương trình gọi models.list, ưu tiên gemini-2.5-flash-lite, nếu không có thì gemini-2.5-flash; chỉ khi tài khoản liệt kê model với generateContent. Không tự chuyển Pro/preview hoặc model khác. Nếu hai model đều không khả dụng thì OFF, báo Codex. Model khả dụng trên tài liệu không thay kiểm tra khóa/tài khoản thực.
5. Sau khi Gemini trả lời riêng thành công, START_AI mới hỏi Bot Token ẩn. Kiểm đúng bot/nhóm đã xác minh và webhook tắt. Không tự thay webhook.
6. Mặc định OFF. Nhập ON rồi Enter. Trong đúng nhóm thử, gửi `@Bot JAT Design thủ đô Việt Nam là gì?`.
7. OFF ngăn gửi mới, ON bật lại, QUIT/Ctrl+C dừng. Request Zalo đã bắt đầu không thể thu hồi. Chỉ tối đa 3 lần thử phản hồi/phiên, đủ 3 tự dừng; OFF/ON không reset bộ đếm. Câu test Gemini riêng là một request bổ sung, không gửi Zalo.

## Ngân sách và dữ liệu

- maxOutputTokens=128, thinkingBudget=0 cho hai model Gemini 2.5 đã chọn, temperature=0.3. Không tăng token khi thiếu đầu ra. Hết quota/HTTP429/timeout: dừng, không retry hoặc fallback sang model khác.
- System prompt mặc định tiếng Việt, 1–2 câu, không quá 50 từ. Hậu xử lý giới hạn 2 câu/50 từ ngay cả khi model không tuân thủ. Prompt tối đa 4000 ký tự, câu hỏi tối đa 1200 ký tự để hạn chế input.
- Chỉ gửi Google phần text câu hỏi hiện tại sau chuỗi @Bot JAT Design; không gửi lịch sử nhóm, raw sender/group ID hoặc token Zalo. Đây vẫn là lọc chuỗi văn bản, không nhận dạng mention entity.
- Key chỉ trong RAM và HTTP header x-goog-api-key, không URL, source, config hoặc log. Nhập lại khi mở phiên mới. Không tự tạo hoặc kích hoạt dịch vụ có phí; dùng hạn mức/quota của khóa bạn cấp. Không cam kết miễn phí.
- Cooldown10 giây, reserve-before-send/dedup qua restart và self/bot/group filter được tái sử dụng nguyên từ AUTO. AI dùng runtime/ai_reply.db riêng, không đụng one_shot.db/auto_reply.db. Không chạy đồng thời AUTO và AI cho cùng token. Timestamp trước ON bị bỏ qua.
- Lỗi Gemini sau reserve cũng dừng/khóa phiên AI một cách bảo thủ, dù có thể chưa gọi Zalo; không tự mở khóa hoặc gửi lại. Các DB cũ giữ nguyên. Status chỉ trạng thái/model/mã lỗi, không câu hỏi/câu trả lời nhóm.

## Bằng chứng và giới hạn

92/92 test offline đạt tại Windows. Chưa xác nhận Gemini live/models.list trên khóa của chủ dự án hoặc 3 câu AI hiển thị trong Zalo khi tạo gói; chương trình có cổng kiểm riêng trước gửi. Không tuyên bố tích hợp live thành công từ unit test.

Tài liệu chính thức đã mở: https://ai.google.dev/api/models ; https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite ; https://ai.google.dev/gemini-api/docs/generate-content/thinking . API REST generateContent chỉ có một user turn, không tools hoặc history. Chưa Railway.
