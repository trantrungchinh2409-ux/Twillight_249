# Win7 — xác minh nhóm trực tiếp, không cần hồ sơ ở máy nhà

Bản này tiếp tục source `jat-design/win7-python38-startup-fix-20261026` tại `19b041e`. Không build EXE, không sửa stable hoặc bản Windows11 đang hoạt động. Root G3 vẫn đóng sẵn và chỉ áp dụng cho HTTPS Zalo. Không cần Codex Desktop hoặc Python ở máy nhà.

## Vì sao CHECK báo E33?

Guard cũ cần `one_shot.db` có biên nhận bot đã gửi thành công và mẫu nhóm DPAPI từ lần thử trước. Máy Win7 đã mất hồ sơ đó, nên không được tạo DB rỗng hoặc ghi giả `api_acknowledged` để làm CHECK xanh.

Bản mới có **loại hồ sơ riêng: xác minh qua sự kiện nhận có mã mới và người dùng xác nhận**. Không gọi sendMessage, không giả biên nhận gửi. Đường đọc hồ sơ cũ vẫn giữ nguyên cho người đang dùng hồ sơ cũ.

## Cách dùng bằng chuột trên Win7

1. Đóng mọi bot/poller cũ, cả trên các máy khác nếu đang chạy cùng token. Giải nén toàn bộ ZIP mới vào **đúng thư mục đang có vault Gemini trên Win7**, cập nhật file chương trình nhưng **giữ nguyên `runtime/` và mọi DB/key còn lại**. Không chỉ chép BAT, không chạy từ trong ZIP.
2. Nhấp **VERIFY_GROUP_WIN7.bat**. Bộ kiểm ENV trước đó không yêu cầu hồ sơ nhóm, nên không bị E33 chặn thao tác này. Không cần mở INIT_PROFILE_WIN7.bat vì BAT cũ đó chỉ dùng để nhập ZIP hồ sơ từ máy khác.
3. Đọc thông báo hồ sơ mới không khôi phục lịch sử đã mất. Gõ **TAO MOI** rồi Enter. Nhập **Bot Token tại CMD bằng nhập ẩn**, không gửi token vào chat/GitHub. Công cụ giữ token trong RAM.
4. Công cụ gọi getMe và getWebhookInfo qua transport chỉ đọc. Nếu webhook đang bật, API lỗi hoặc khóa poller/vault đang bị giữ: dừng; không tự đổi webhook. Không gửi thử cho đến khi cửa sổ hiện **READY** và mã `JAT-VERIFY-...`.
5. **Chỉ khi READY:** trong đúng nhóm thử muốn cho bot hoạt động, chọn @Bot JAT Design thật trong Zalo rồi gửi kèm **đúng mã vừa hiện**. Gửi một tin mới, không lấy mã cũ, không gửi ở nhóm khác. Ví dụ hình thức: `@Bot JAT Design JAT-VERIFY-<mã của phiên này>`. Không nhập ID nhóm; nhóm được lấy từ sự kiện thật Zalo trả về.
6. Đợi tối đa khoảng 5 phút. Công cụ chỉ nhận `message.text.received`, GROUP, người gửi không phải bot/self, đúng mã tách từ và timestamp mới hợp lệ. Nếu giờ máy lệch khiến sự kiện bị từ chối, dừng để kiểm đồng hồ; không bỏ lọc thời gian. Công cụ không ghi/in tên nhóm, ID người dùng hoặc nội dung tin nhắn.
7. Khi hiện **RECEIVED GROUP**, xác nhận rằng bạn vừa gửi mã ở đúng nhóm thử. Gõ **XAC NHAN** để lưu; Enter khác sẽ hủy và không tạo hồ sơ. Việc này xác nhận nhóm bằng hành động của bạn và API, không chứng nhận parser mention/reply.
8. Chỉ khi hiện **PASS LOCAL PROFILE**, chạy **CHECK_WIN7.bat**. Cần thấy **PASS READY**; bot vẫn chưa gửi tin. Nếu CHECK báo lỗi, dừng ở mã đó, không xóa DB để né lỗi.
9. Sau CHECK PASS, mở **START_WIN7_PYTHON.bat**, nhập token ẩn như luồng cũ. Bot vẫn mặc định OFF. Chỉ tự gõ ON sau các kiểm tra khởi động đạt. Có thời gian nghỉ an toàn ít nhất **5 phút từ lúc tạo hồ sơ**; đây không phải lỗi TLS hoặc mất key.

Nếu không nhận được sự kiện trong hạn, không có hồ sơ được tạo. Chỉ đọc các mã kỹ thuật trong cửa sổ để chẩn đoán; không xuất runtime hoặc gửi token/ID lên chat. Việc polling có thể tiêu thụ sự kiện đang chờ; vì vậy phải đóng poller khác trước, và công cụ không phát lại các tin đã đọc.

## Các file runtime được tạo sau xác minh thật

- `one_shot.db`: schema `deliveries` hiện có + bảng `group_verifications` cho bằng chứng nhận. Trạng thái mới là `verified_receive_only:<hash>`, **không phải** `api_acknowledged` hoặc phép thử gửi thành công.
- `local_group_profile.dpapi`: nhóm thật lấy từ API và metadata tối thiểu, mã hóa Windows DPAPI theo tài khoản/máy hiện tại. Không lưu token, nội dung tin nhắn, sender ID hoặc toàn payload. Event ID và mã phiên chỉ lưu hash; bot chỉ lưu hash để đối chiếu với getMe khi khởi động.
- `ai_reply.db`: nếu chưa có, tạo đúng schema bằng `State` và `ManagedResponder` hiện có. Nếu đã có, giữ toàn bộ dedup, số lượt, cooldown, Google waits và dữ liệu khác. Không xóa/reset lịch sử hiện có. Sự kiện xác minh được đánh dấu đã tiêu thụ để không bị dùng làm câu hỏi bot về sau.
- `profile-import.pending`: guard có sẵn được dùng trong lúc ghi. Chỉ gỡ khi đã đọc lại bằng chứng thành công. Nếu bị gián đoạn, giữ file và dữ liệu, CHECK/START sẽ chặn; không tự xóa marker.

Không ghi đè `one_shot.db`, mẫu legacy, hồ sơ mới hoặc pending đã tồn tại. Có `auto_block`/uncertain-send trong DB hiện có thì dừng trước khi ghi. Vault Gemini không bị đọc/ghi lại bởi quy trình khởi tạo nhóm; khóa vault chỉ ngăn chạy đồng thời.

## Lịch sử từ máy nhà chưa thể khôi phục

Hồ sơ mới chỉ chứng minh nhóm và bot của **phiên nhận hiện tại**. Không thể tái tạo lịch sử gửi, bộ đếm hoặc những kết quả chưa chắc chắn đã nằm trong dữ liệu bị xóa. Không tuyên bố đã khôi phục chúng.

Để tránh việc có ngay ngân sách mới sau khi mất lịch sử, lúc khởi tạo áp dụng pause ít nhất 300 giây; pause dài hơn và Google waits hiện có vẫn giữ nguyên. Không gửi thông báo nhóm trong pause khởi tạo. Sau đó engine cũ vẫn quản lý 10 lượt/120 giây, nghỉ 300 giây, cooldown10, DPAPI, failover và chống gửi trùng như trước. Chỉ tin mới sau khi bạn bật ON mới đủ điều kiện được engine xử lý.

Không chạy lại bản ở nhà đồng thời. Sau này lấy được hồ sơ cũ, không chép đè hoặc nhập chồng để mất các bản ghi vừa phát sinh ở Win7. Bản này không tự hợp nhất hai lịch sử.

`INIT_PROFILE_WIN7.bat`/`EXPORT_PROFILE_WIN7.bat` cũ vẫn phục vụ định dạng legacy từ bản gửi thử. Export/import legacy chưa được mở rộng để chuyển hồ sơ receive-only mới; không dùng chúng để thay/di chuyển hồ sơ mới giữa máy lúc này. Giữ nguyên máy/tài khoản và runtime; nếu cần chuyển, phải xử lý riêng mà không reset DB.

## Chẩn đoán an toàn

| Mã/hiện tượng | Xử lý |
| --- | --- |
| EXISTING_PROFILE | Đã có hồ sơ hoặc pending. Giữ file, không xóa để chạy lại |
| WEBHOOK_ENABLED | Không polling; công cụ không xóa webhook. Báo mã để xử lý riêng |
| NO_MATCHING_EVENT | Không có sự kiện đủ điều kiện hoặc lỗi polling. Đọc dòng loại/mã API; chưa có hồ sơ |
| SEND_UNCERTAIN | Có guard gửi chưa rõ; không tạo hồ sơ để né guard |
| STATE_INVALID | DB AI hỏng/sai schema/bị khóa; giữ DB |
| PROOF_INVALID / CHECK E38 | Bằng chứng/DB/bot không khớp. Không làm giả receipt hoặc sửa ID |
| CHECK E40 | Có pending do ghi chưa hoàn tất; giữ mọi file, không bật bot |
| Exit51 | API getMe/getWebhookInfo lỗi; chỉ in kind/code an toàn |
| Exit52 | Khóa/DPAPI/file có lỗi; giữ pending/DB nếu có |

CHECK READY là kiểm offline, không chứng minh quyền gửi API hoặc quota Gemini. Bằng chứng live nhận nhóm chỉ được xác nhận sau khi bạn thực sự hoàn tất các bước READY → gửi mã → XAC NHAN tại máy công ty.

## Căn cứ API và giới hạn kiểm thử

Tài liệu getUpdates chính thức: https://docs.zaloplatforms.com/docs/BOT/apis/getUpdates (đọc lại HTTP200 ngày27/10/2026). Source dùng đúng transport/getMe/getWebhookInfo/getUpdates hiện có, timeout long poll30s/HTTP40s, không thay parser GROUP hoặc đoán group ID. Tài liệu cảnh báo không polling đồng thời khi webhook được thiết lập; chương trình dừng nếu có URL.

Test offline chỉ dùng event/transport/DPAPI double trong thư mục tạm, không phải bằng chứng nhóm thật. Không có live token/key tại môi trường chuẩn bị ZIP. Xem VALIDATION_LOCAL_GROUP_WIN7.md để biết phần nào đã kiểm và phần nào phải nghiệm thu trên Win7.
