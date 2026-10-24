# JAT Design — thử nhận sự kiện thật trên Windows 11

Nhấp đúp **START_TEST.bat** trong thư mục này. Python 3.10+ được kiểm tra tự động; chương trình dùng thư viện chuẩn, không cần pip hoặc API AI.

1. Dán Bot Token vào cửa sổ khi được hỏi. Ký tự không hiển thị; nhấn Enter. Không dán token vào chat. Token không được lưu ra tệp.
2. Chương trình gọi getMe và getWebhookInfo. Nếu hiện **WEBHOOK ĐANG BẬT**, nó dừng trước polling. Báo Codex dòng này để duyệt việc chuyển tạm và kế hoạch khôi phục. Bản thử không có lệnh xóa/đổi webhook.
3. Nếu webhook không có URL, chọn A để thử @bot thật. Khi hiện **ON — Đang chờ**, mới chọn bot trong danh sách @ của Zalo rồi gửi tin trong nhóm.
4. Nhận đúng một sự kiện thì chương trình tự dừng. **GROUP** mới là sự kiện nhóm; PRIVATE không đạt mục tiêu nhóm. Mẫu cấu trúc đã che nằm trong `runtime/event_*.json` và bị loại khỏi Git/ZIP.
5. Thử B: reply không @, C: mention người khác, D: tin thường ở các phiên sau. Nhãn do người thử chọn, không phải kết luận của parser. Sự kiện có thể là tin đã chờ từ trước; đối chiếu thời điểm gửi để tránh gán nhãn nhầm.

ON/OFF ở bản này là bật/tắt nhận: mở để ON, Ctrl+C/đóng cửa sổ để OFF. **Gửi trả lời luôn OFF**; không thể bật từ bản thử này. Chưa triển khai câu “JAT Design đã kết nối thành công” hoặc tự xác định mention. Chỉ làm sau khi có mẫu thật và chủ dự án duyệt gửi.

Chỉ một bản thử cho cùng token trong cùng phiên đăng nhập Windows. Không chạy poller khác trên máy/Cloudflare/Railway cùng lúc. Khóa local không ngăn máy chủ khác. Một phiên chờ khoảng 5 phút (request đang chờ có thể kết thúc muộn tối đa 40 giây), lỗi liên tiếp tối đa 3 lần, không retry vô hạn.

Chưa gửi tin nên không có nguy cơ spam từ bản thử. Dedup/cooldown cho gửi sẽ được nghiệm thu khi nối parser thật vào engine cũ. Code cũ và Worker giữ nguyên, ngoài mở rộng transport đọc getWebhookInfo và mã lỗi an toàn. Không deploy Cloudflare, không gọi testWebhook, không xoay token.

## Nguồn kỹ thuật đã đối chiếu

- Zalo: https://docs.zaloplatforms.com/docs/BOT/apis/getUpdates và /getWebhookInfo; polling POST, object đơn, timeout chuỗi 30 giây; HTTP timeout 40 giây; không offset Telegram. Production được tài liệu khuyên dùng webhook.
- Nhóm: https://docs.zaloplatforms.com/docs/BOT/best-practices/build-bot-interaction-with-group — có mention và quote/reply, chưa xác định discriminator từ mẫu bot này.
- Dự án tham khảo: https://github.com/openclaw/openclaw/blob/main/extensions/zalo/src/api.ts — cách dùng object đơn và timeout long polling. Không sao chép source/license; chỉ đối chiếu hợp đồng. Tài liệu OpenClaw tự ghi experimental, không chứng nhận bot JAT đã hoạt động.

## Các giai đoạn tiếp theo

## Chuyển tạm sang polling (chủ dự án đã duyệt ngày 24/10/2026)

Đóng cửa sổ START_TEST cũ rồi mở `SWITCH_TO_POLLING.bat`. Nhập Bot Token ẩn, tiếp theo là **ZALO_WEBHOOK_SECRET cũ** (không phải Bot Token). Chương trình lưu URL và secret do bạn nhập vào `runtime/webhook_backup_*.bin`, mã hóa DPAPI theo tài khoản Windows hiện tại. Bản sao phải đọc/giải mã kiểm lại thành công trước khi gọi deleteWebhook. Không đổi/xóa Worker, không reset token. Không có secret cũ thì dừng trước mutation; không tự tạo secret thay thế. Secret do bạn nhập chưa được đối chiếu với secret trên Worker, vì Cloudflare/Zalo không cho đọc lại giá trị đó.

Chỉ khi getWebhookInfo sau delete trả URL rỗng mới báo **WEBHOOK ĐÃ TẮT**. Lúc đó mở START_TEST.bat, chọn A, chờ ON rồi @bot thật trong nhóm. Công cụ vẫn không gửi trả lời.

Khôi phục: đóng mọi poller rồi mở `RESTORE_WEBHOOK.bat`, nhập token và gõ KHOI PHUC. Nó dùng bản sao gần nhất cùng bot và tài khoản Windows; nếu webhook khác đang bật thì từ chối ghi đè. Không chuyển file sao lưu sang máy/tài khoản khác. Không đưa runtime lên chat/Git hoặc ZIP. Khôi phục URL không chứng minh callback hết lỗi 403; công cụ phân biệt URL khớp với callback được API xác nhận. Không tự retry mutation khi timeout.

Các dòng status trong runtime chỉ ghi trạng thái không có credential. Nếu thao tác lỗi sau khi bắt đầu delete, báo Codex; giữ nguyên bản sao, không xóa hoặc chạy restore/switch lặp lại tùy tiện.

Sự kiện nhóm thật → đối chiếu A/B/C và bot ID → parser/test → chủ dự án duyệt gửi một câu → nghiệm thu chống trùng/cooldown/ON-OFF gửi → Railway một instance và restart → Gemini. Không tự mở dịch vụ trả phí. Giữ Cloudflare dự phòng và cần xác nhận secret webhook cũ còn khả dụng trước khi chuyển; getWebhookInfo không đọc lại được secret đó.
