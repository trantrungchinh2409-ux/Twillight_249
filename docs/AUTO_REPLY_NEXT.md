# Bước kế tiếp: auto reply khi @bot, không dùng mã

Giữ mốc stable-live-20261024, không sửa transport/vòng polling/adapter gửi đã chạy. Chưa bật auto reply ở mốc này.

## Cổng còn thiếu

Mẫu A đã nhận GROUP nhưng message_type chỉ giữ fingerprint, chưa có mẫu B reply đúng tài khoản bot. B cũ reply tin thành viên không kiểm tra được việc reply bot có bị coi nhầm là mention hay không. Nay đã có tin bot thật, chọn B trong START_TEST và reply đúng “JAT Design đã hoạt động thành công!” mà KHÔNG @bot. Cần đối chiếu A/B trước khi chốt parser. Có thể cần C mention người khác hoặc D gõ tên bot nếu schema chưa đủ chứng minh discriminator/bot đích. Không có event không tự chứng minh parser đúng.

## Phạm vi chuẩn bị

- Nhánh phát triển kế thừa mốc stable, thêm parser ở biên; không đoán field hoặc dựa vào text tên hiển thị. Thiếu discriminator: OFF/fail-closed.
- ON/OFF rõ ràng: mặc định OFF; chỉ chuyển ON sau khi token/bot, nhóm cho phép và parser đã kiểm. OFF/Ctrl+C ngăn gửi mới, dừng sạch. Không coi đóng cửa sổ là hủy được request gửi đang diễn ra.
- Chỉ nhóm allowlist được chủ dự án chọn, không tự học nhóm từ bất kỳ tin đến. Lưu ID cấu hình local mã hóa, không trong source/Git.
- Tái sử dụng reserve-before-send của SQLite: hash bot/group/message, chống trùng qua restart; một lần xử lý mỗi event. Cooldown ít nhất 5 giây/nhóm; không retry send khi timeout chưa rõ kết quả. Nêu rõ có thể mất phản hồi, không hứa exactly-once.
- Giữ khóa one_shot.db của lần thử thành công. Trạng thái auto đặt riêng, không dùng cách reset approval one-shot để bật auto.
- Câu thử tự động ban đầu giữ “JAT Design đã hoạt động thành công!”. Không AI, không gửi tin chủ động hay reply self/bot.

## Nghiệm thu trước Railway

@bot thật: một câu. Reply bot không @: im lặng. Mention người khác/gõ tên bot: im lặng. Tin riêng/nhóm ngoài allowlist/self/bot: im lặng. Duplicate/restart không gửi lại; cooldown chặn spam; OFF chặn gửi. Kết quả mock và kết quả Zalo thật ghi riêng.

Chỉ sau nghiệm thu auto thật mới chuẩn bị Railway một instance, lưu trạng thái bền, không sleep và restart/rollback có kiểm soát. Chưa tạo dịch vụ trả phí. Production polling có hạn chế giao event theo tài liệu Zalo; cần thông báo trước khi chốt vận hành 24/7. Gemini vẫn hoãn.
