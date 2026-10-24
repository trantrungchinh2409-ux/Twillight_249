# JAT Design AUTO — bản thử Windows 11

Chỉ là lọc chuỗi văn bản phân biệt hoa/thường, không xác thực mention entity. Tin GROUP trong đúng nhóm thử chứa nguyên chuỗi `@Bot JAT Design` sẽ nhận đúng `JAT Design đã nhận tin!`. Reply không chứa chuỗi này im lặng; reply có chuỗi vẫn được xử lý theo lựa chọn của chủ dự án. Tin riêng, nhóm khác, self/bot và thiếu is_bot=false bị bỏ qua.

## Một cú nhấp

1. Đóng START_TEST, COMPARE_MENTIONS, SEND_ONCE hoặc poller khác.
2. Mở **START_AUTO.bat**, nhập Bot Token ẩn.
3. Chương trình kiểm getMe, webhook đang tắt, token khớp bot của one-shot thành công và giải mã ID nhóm từ mẫu A đã xác minh. Không tự học thêm nhóm.
4. Mặc định **OFF**. Nhập **ON** rồi Enter để bật. Gửi `@Bot JAT Design xin chào` trong nhóm thử.
5. Nhập **OFF** rồi Enter để ngăn gửi mới; **ON** để bật lại; **QUIT** để kết thúc. Ctrl+C dừng tiến trình. OFF không thu hồi được request gửi đã bắt đầu; QUIT có thể chờ request nhận hiện tại kết thúc (tối đa khoảng 1 phút). Không cần mã JAT-.

Nếu token không đúng bot, webhook bật, thiếu/không giải mã được mẫu nhóm hoặc có khóa gửi chưa rõ kết quả: dừng OFF, không thay cấu hình để cố chạy.

## Giới hạn an toàn

- Cooldown **10 giây** cho nhóm, lưu bền qua restart. Tin trong cooldown bị bỏ qua, không xếp hàng gửi muộn.
- Tối đa **5 lần thử gửi trong một phiên**; OFF/ON không reset bộ đếm. Đủ 5 tự dừng. Phiên mới có bộ đếm mới, vẫn giữ chống trùng/cooldown.
- Hash bot/nhóm/event và reserve trước send; event cũ đã xử lý không gửi lại. Tin có timestamp trước lúc ON hoặc thiếu timestamp millisecond hợp lệ bị bỏ qua.
- Crash/timeout/ack không rõ: lưu guard bền và dừng OFF. Phiên mới vẫn bị chặn cho đến khi kiểm tra thủ công; không tự gửi lại, không xóa DB để mở khóa.
- Khóa Windows TokenLock tái sử dụng; không chạy poller trên máy/chủ khác với cùng token. Khóa local không kiểm soát được máy chủ khác.
- Lỗi nhận thật dừng, không retry mò. API 408 của getUpdates vẫn là hết lượt chờ rỗng như bản đã chạy; không áp dụng cho HTTP 408 hoặc sendMessage.

Token chỉ ở RAM. `runtime/auto_reply.db` và `auto_reply_status.json` riêng, không sửa/xóa `one_shot.db`. Không đưa runtime vào Git/ZIP. Status không lưu text chat, token hoặc raw ID.

## Cấu hình nhóm và phục hồi

Bản này dùng mẫu A local đã mã hóa `mention_compare_20261024T080236_974d67_A.bin` và kiểm token với hash bot trong one_shot.db. Vì vậy tải source sang máy khác không tự cấu hình được; thiếu dữ liệu thì OFF. Không cho phép sửa tay group ID trong source. Mốc GitHub `jat-design/stable-live-20261024` giữ nguyên làm dự phòng.

83/83 test offline đạt trên Windows, gồm lọc chuỗi, OFF, nhóm sai, self/bot, chống trùng, cooldown, 5 lần/phiên, backlog trước ON, guard qua restart khi timeout. Đã đọc kiểm mẫu A mã hóa thực tế (chỉ kiểm thuộc tính, không xuất nội dung/ID). Chưa nghiệm thu AUTO trả lời thật cho đến khi chủ dự án nhìn thấy tin mới trong Zalo.

Không Railway, Gemini, đổi webhook/token hoặc sửa SEND_ONCE. Không build EXE lại. Tái sử dụng Transport, OfficialAPI.sendMessage, receive_one và State đã có.
