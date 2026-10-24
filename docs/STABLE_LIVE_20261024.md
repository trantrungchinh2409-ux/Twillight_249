# Mốc khôi phục: Zalo thật đã nhận và gửi — 24/10/2026

## Bằng chứng

Chủ dự án xác nhận lúc 14:50 UTC+7 ngày 24/10/2026: @Bot JAT Design kèm mã thử trong nhóm; tài khoản bot hiển thị đúng “JAT Design đã hoạt động thành công!”.

Đã đối chiếu dữ liệu local:
- one_shot_receipt.json: at_utc=2026-10-24T07:50:46.111232+00:00, outcome=api_acknowledged, group_event=true, automatic_retry=false.
- one_shot_poll_status.json: event_accepted lúc 07:50:45.892169 UTC, poll_errors=0, rejected_events=0.
- one_shot.db read-only: integrity_check=ok, hai dòng; trạng thái api_acknowledged và api_acknowledged kèm hash ID. Không lưu raw ID/token ở báo cáo công khai.
- Code chạy thật là commit local 18c42e3 (đầy đủ SHA xem Git history). Mốc này chỉ bổ sung báo cáo/chuẩn bị, không đổi code getUpdates/sendMessage hoặc bộ lọc gửi đã chạy.

Nhận GROUP thật + API ack + xác nhận người dùng nhìn thấy tin: phép thử nhận/gửi một câu **đã đạt**. Không dùng unit test để thay bằng chứng này.

## Giới hạn

Đây là gửi một lần bằng mã chọn nhóm, không phải auto responder mention đã nghiệm thu. mention_verified=false. getUpdates API error_code=408 được xử lý là lượt chờ rỗng; HTTP 408/network timeout vẫn là lỗi. Không thêm Gemini/Railway; Cloudflare giữ nguyên, webhook đã tắt tạm để polling.

## Khôi phục

Nhánh mốc: jat-design/stable-live-20261024. Dùng source ở nhánh này để đối chiếu hoặc phục hồi vào thư mục riêng sau khi dừng poller. Giữ runtime hiện tại và one_shot.db; không sao chép DB mẫu hay xóa bản ghi để gửi lại. Source ZIP sạch không chứa trạng thái người dùng; giải nén source mới KHÔNG tự phục hồi khóa chống trùng của máy cũ. Trước khi chạy phục hồi phải giữ/mang đúng trạng thái runtime hiện tại vào đúng vị trí, tránh khởi động bản sao trống gửi thêm.

Backup webhook .bin mã hóa chỉ giữ local và chỉ giải mã trên tài khoản Windows gốc. Không push runtime, token, khóa webhook, raw chat hoặc DB lên GitHub. Không chạy RESTORE_WEBHOOK trong khi poller còn chạy. Khôi phục URL không bảo đảm callback Cloudflare hết lỗi 403 cũ.
