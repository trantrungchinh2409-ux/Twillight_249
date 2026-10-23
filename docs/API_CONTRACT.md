# Hợp đồng Zalo Bot API — đã xác minh một phần

Ngày 23/10/2026, sau các lần 403 trước đó, tài liệu tại `docs.zaloplatforms.com` đã trả HTTP 200. Đã đọc trực tiếp:

- https://docs.zaloplatforms.com/docs/BOT/apis/getUpdates
- https://docs.zaloplatforms.com/docs/BOT/apis/sendMessage
- https://docs.zaloplatforms.com/docs/BOT/apis/getMe
- https://docs.zaloplatforms.com/docs/BOT/webhook
- https://docs.zaloplatforms.com/docs/BOT/best-practices/build-bot-interaction-with-group
- https://docs.zaloplatforms.com/docs/BOT/error_code

## Đã xác minh và triển khai

POST JSON tới `https://bot-api.zaloplatforms.com/bot${BOT_TOKEN}/<method>`. Không log URL chứa token. Không theo redirect và không tắt TLS verification.

- `getMe`: body `{}`, `ok: true`, `result.id` là ID bot.
- `getUpdates`: body có `timeout`, bảng đặc tả ghi String, code mẫu dùng số 30. Client chọn `"30"` theo bảng; socket timeout 40 giây. Response là object sự kiện như trang Webhook, không giả định batch, update_id hay offset Telegram. Không tự thêm acknowledgement chưa được tài liệu xác nhận.
- `sendMessage`: body `chat_id` và `text` (1..2000 ký tự). Thành công trả `ok: true`, `result.message_id`, `result.date`. Client kiểm tra message_id; không tự retry gửi khi kết quả không rõ.
- Sự kiện text: `result.event_name = message.text.received`, `result.message` chứa `from.id`, `from.is_bot`, `chat.id`, `chat.chat_type`, `text`, `message_id`. Parser dùng mẫu PRIVATE đã được tài liệu cung cấp. Những loại event khác được nhận diện và không gửi trả lời.

Tài liệu nói getUpdates không hoạt động khi đã thiết lập webhook; chương trình không tự xóa webhook. Tài liệu khuyến nghị polling cho development, webhook cho production. Dự án đang làm V0.1 thử nghiệm theo yêu cầu polling.

## Chưa xác minh: điều kiện mention trong nhóm

Trang hướng dẫn nhóm ghi nguyên tắc bot nhận sự kiện khi:

1. Thành viên trả lời trực tiếp/trích dẫn tin nhắn bot.
2. Thành viên gõ @ và chọn tên bot.

Trang này dẫn về mẫu Webhook nhưng mẫu chỉ có PRIVATE. Chưa thấy field JSON phân biệt hai trường hợp hoặc chứa ID được mention trong các trang đã đọc. Không được suy luận “mọi event GROUP đều là mention”. Không dùng kiểm tra chuỗi tên hiển thị để thay thế mention thực.

`parse_event` từ chối GROUP bằng `MentionContractNotVerified`, kể cả raw object có field `mentions` chưa xác minh. Các test GROUP của parser là biến thể âm tính tổng hợp, không phải payload thu từ Zalo. `Event.mentioned_ids` và `MockAPI` vẫn là hợp đồng nội bộ. Engine đã xử lý đúng điều kiện nếu nhận được metadata chuẩn hóa đáng tin cậy; adapter chưa được phép tạo metadata này từ field đoán.

`--live` bị khóa trước khi đọc token/poll. `--check-api` chỉ gọi getMe, có thể nhập token ẩn hoặc đọc binding ZALO_BOT_TOKEN; không gửi/poll. Không có token Zalo để chạy kiểm tra thực tế trong phiên này.

## File người dùng cung cấp

Giữ nguyên bản sao tại `docs/zalo-bot-error-code.user.md`. Bảng số 400/401/403/404/408/429 phù hợp trang `error_code` đã đọc. Tuy nhiên các đoạn refresh_token, OA ID, endpoint `/v3.0/oa/message`, hạn 24h, limiter 10 req/s và lịch refresh 5 phút không xuất hiện trong trang chính thức vừa kiểm tra. Không triển khai các giả định OA đó cho Bot API.

Không làm theo khuyến nghị log nguyên description trong file đính kèm: description có thể chứa dữ liệu nhạy cảm. Lỗi transport/API hiện được thay bằng thông báo cố định, không log body hoặc URL.

## Cổng còn lại

Cần schema/mẫu mention nhóm và mẫu reply-only đã che dữ liệu nhạy cảm để xác minh cách phân biệt. Sau đó thêm parser và test có nguồn, nối vòng polling có dừng/backoff, kiểm thử với bot thật và build/chạy Windows. Không tuyên bố V0.1 đạt yêu cầu khi cổng mention này chưa hoàn tất.
