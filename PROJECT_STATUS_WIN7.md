# JAT Design — mốc Win7 đã được người dùng xác nhận chạy thành công

Ngày ghi nhận: **27/10/2026, giờ Việt Nam**.

Người dùng xác nhận: **“ok đã chạy ngon lưu dự án”** sau khi khởi tạo hồ sơ nhóm trực tiếp trên Win7. Đây là xác nhận vận hành thực tế từ người dùng, không phải kết luận dựa trên mock test. Không có log hội thoại, token, API key hoặc runtime riêng được đưa lên GitHub.

## Mốc source được giữ lại

- Repository: https://github.com/trantrungchinh2409-ux/Twillight_249
- Nhánh: `jat-design/win7-local-group-profile-20261027`.
- Commit source/ZIP được bàn giao: **`53f59763c93ad05dcc2d914c38478083e657ddf6`**.
- Tag lưu mốc source: **`jat-design-win7-accepted-20261027`**.
- Kế thừa bản startup `19b041e`, tiếp tục dự án cũ, không build lại EXE và không sửa các nhánh stable hoặc bản Windows11 đang hoạt động.

## Bản tải đã được bàn giao

[ZIP JAT Design Win7 Python38 LocalGroup 27/10/2026](https://github.com/trantrungchinh2409-ux/Twillight_249/raw/53f59763c93ad05dcc2d914c38478083e657ddf6/downloads/JAT-Design-Win7-Python38-LocalGroup-20261027.zip)

SHA256:
```
8b7bca8f9769e3bcdcc4f7197f206e7f0b1b646465c4ad24cd073463263ac17f
```

ZIP đã được tải lại HTTP200, kiểm checksum và CRC trước bàn giao. Không tạo lại ZIP chỉ để ghi nhận trạng thái, để giữ nguyên artifact người dùng đã thử.

## Những vấn đề đã đi qua

1. Win7 Professional SP1 x64: Python3.8.10 và SQLite3.35.5 đọc/ghi hoạt động; chạy source trực tiếp, không dùng EXE cũ lỗi `_sqlite3`.
2. Zalo HTTPS mặc định fail19; người dùng kiểm T2 root G3 PASS, T3 root+intermediate PASS, Google PASS. Root G3 đúng pin được đóng sẵn và chỉ gắn vào context Zalo, không sửa Windows Store hoặc Gemini trust.
3. Startup đã đọc được Gemini API vault; CHECK báo E33 vì thiếu `one_shot.db` sau khi bản cũ trên Win7 bị xóa và không truy cập được hồ sơ ở máy nhà.
4. Bổ sung VERIFY_GROUP_WIN7: getMe/getWebhookInfo/getUpdates chỉ đọc, nhận mã mới do người dùng chủ động gửi trong nhóm, yêu cầu xác nhận rồi lưu hồ sơ DPAPI và receipt receive-only riêng. Không đoán ID, không làm giả biên nhận gửi, không gửi tin trong xác minh.
5. Người dùng từng báo bộ lọc không khớp, sau đó đính chính **“nãy mk nhầm nhập đc rồi”**. Công việc thêm diagnostic được tạm dừng, không phát hành và không đưa vào mốc source đang chạy.
6. Người dùng tiếp tục xác nhận bản hiện tại chạy tốt. Giữ nguyên source và artifact này làm mốc khôi phục.

Đã có 146 test offline đạt, 4 test cần Windows/native CA được bỏ qua ở phiên chuẩn bị bản LocalGroup. Xác nhận mới của người dùng là bằng chứng vận hành bổ sung; không suy diễn thành đã chạy lại mọi test native, mọi tình huống failover, revocation hoặc mention entity. Các báo cáo kiểm thử lịch sử vẫn được giữ nguyên và được đọc cùng ghi nhận nghiệm thu này.

## Dữ liệu và logic phải giữ nguyên khi tiếp tục

- Gemini, API vault nhiều key, DPAPI, Zalo polling, 10 lượt/120 giây, nghỉ300 giây, cooldown, failover, dedup và uncertain-send guard hiện có.
- Root G3 SHA256 DER: `31AD6648F8104138C738F39EA4320133393E3A18CC02296EF97C2AC9EF6731D0`.
- Không thay global SSL context, không đặt SSL_CERT_FILE toàn tiến trình, không tắt TLS/hostname.
- Không xóa/reset DB; không chạy hai bản bot cùng token song song.
- Hồ sơ mới không giả khôi phục lịch sử đã mất. Dữ liệu còn lại trên Win7 được bảo toàn; pause khởi tạo ít nhất5 phút đã được áp dụng.

## Phạm vi “lưu dự án”

GitHub lưu **source, tài liệu, ZIP ứng dụng và tag phiên bản**. Kho Gemini DPAPI, hồ sơ nhóm thật, database và token của máy công ty **không nằm trong GitHub hoặc ZIP**; chúng vẫn ở `runtime/` trên máy Win7. Không thể sao lưu chúng từ phiên trình duyệt này vì không có truy cập filesystem máy công ty.

Khi cập nhật hoặc di chuyển thư mục, giữ nguyên runtime và tài khoản Windows. Không coi ZIP source là bản sao lưu đầy đủ dữ liệu vận hành. Định dạng export/import legacy cũ chưa được mở rộng cho hồ sơ receive-only mới; không nhập chồng hồ sơ ở nhà lên lịch sử vừa phát sinh trên Win7.

## Hướng dẫn cho phiên tiếp theo

Đọc file này trước, checkout đúng nhánh/mốc source. Ưu tiên giữ bản đã được người dùng xác nhận hoạt động. Chỉ sửa khi có yêu cầu mới hoặc lỗi tái hiện cụ thể. Không áp dụng nhánh diagnostic đang tạm dừng nếu người dùng không cần nữa; không lấy thay đổi Cloudflare cũ sang bot Win7. Không build EXE hoặc chạy vòng lặp CI để thay bản đang hoạt động.
