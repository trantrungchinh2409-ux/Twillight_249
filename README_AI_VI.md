# JAT Design AI — thử tối đa 3 phản hồi thật

Mốc AUTO đã thành công được giữ trên nhánh `jat-design/stable-auto-20261024` và ZIP dự phòng. START_AUTO/AutoResponder/Transport/getUpdates/sendMessage không đổi. START_AI ghép một adapter Gemini trước lời gọi gửi có sẵn; không viết lại bot.

## Chạy

1. Đóng START_AUTO và mọi poller khác.
2. Nếu muốn, sửa SYSTEM_PROMPT.txt cạnh START_AI.bat. Không đặt khóa/token vào prompt. File đọc lúc mở chương trình, không tự đọc lại giữa phiên.
3. Mở TEST_GEMINI.bat để chỉ kiểm model và một câu Gemini, không cần token Zalo. Hoặc mở START_AI.bat: nó tự thực hiện bước kiểm thử Gemini trước.
4. Nhập Gemini API key ẩn. Chương trình gọi models.list để chọn gemini-3.5-flash-lite nếu tài khoản liệt kê model với generateContent. Model 2.5 Flash-Lite đã trả 404 trong phép thử của chủ dự án, nên không chọn lại. Không tự chuyển Pro/preview hoặc dò model khác. Không có 3.5 Flash-Lite thì OFF, báo Codex. Có tên trong models.list chưa chứng minh generateContent dùng được; phải qua một request tạo câu trả lời thật, không tự retry. Thành công mới ghi runtime/gemini_check.json, không ghi key/prompt/response text.
5. Sau khi Gemini trả lời riêng thành công, START_AI mới hỏi Bot Token ẩn. Kiểm đúng bot/nhóm đã xác minh và webhook tắt. Không tự thay webhook.
6. Mặc định OFF. Nhập ON rồi Enter. Trong đúng nhóm thử, gửi `@Bot JAT Design thủ đô Việt Nam là gì?`.
7. OFF ngăn gửi mới, ON bật lại, QUIT/Ctrl+C dừng. Request Zalo đã bắt đầu không thể thu hồi. Lần thử đầu tối đa 3 lượt phản hồi, lưu bền cả khi đóng/mở chương trình; đủ 3 tự dừng, không tự reset quota. Câu test Gemini riêng là một request bổ sung, không gửi Zalo.

## Ngân sách và dữ liệu

- maxOutputTokens=128, thinkingLevel=minimal cho Gemini 3.5 Flash-Lite, temperature=0.3. Không tăng token khi thiếu đầu ra. Hết quota/HTTP429/timeout/404: dừng, không retry hoặc fallback sang model khác. Minimal không phải cam kết tuyệt đối không có thought tokens.
- System prompt mặc định tiếng Việt, 1–2 câu, không quá 50 từ. Hậu xử lý giới hạn 2 câu/50 từ ngay cả khi model không tuân thủ. Prompt tối đa 4000 ký tự, câu hỏi tối đa 1200 ký tự để hạn chế input.
- Chỉ gửi Google phần text câu hỏi hiện tại sau chuỗi @Bot JAT Design; không gửi lịch sử nhóm, raw sender/group ID hoặc token Zalo. Đây vẫn là lọc chuỗi văn bản, không nhận dạng mention entity.
- Key chỉ trong RAM và HTTP header x-goog-api-key, không URL, source, config hoặc log. Nhập lại khi mở phiên mới. Không tự tạo hoặc kích hoạt dịch vụ có phí; dùng hạn mức/quota của khóa bạn cấp. Không cam kết miễn phí.
- Cooldown10 giây, reserve-before-send/dedup qua restart và self/bot/group filter được tái sử dụng nguyên từ AUTO. AI dùng runtime/ai_reply.db riêng, không đụng one_shot.db/auto_reply.db. Không chạy đồng thời AUTO và AI cho cùng token. Timestamp trước ON bị bỏ qua.
- Lỗi Gemini sau reserve cũng dừng/khóa phiên AI một cách bảo thủ, dù có thể chưa gọi Zalo; không tự mở khóa hoặc gửi lại. Các DB cũ giữ nguyên. Status chỉ trạng thái/model/mã lỗi, không câu hỏi/câu trả lời nhóm.

## Bằng chứng và giới hạn

96/96 test offline đạt tại Windows. Model 2.5 đã list được nhưng generateContent HTTP404 ở máy chủ dự án; không có response body cũ để kết luận lý do dự án mới. Chưa xác nhận Gemini 3.5 live trên khóa của chủ dự án hoặc câu AI hiển thị trong Zalo; phải qua TEST_GEMINI trước. Không tuyên bố tích hợp live thành công từ unit test.

Tài liệu chính thức đã mở: https://ai.google.dev/api/models ; https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite ; https://ai.google.dev/gemini-api/docs/generate-content/thinking . API REST generateContent chỉ có một user turn, không tools hoặc history. Chưa Railway.
