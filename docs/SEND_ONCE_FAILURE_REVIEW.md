# Kiểm tra SEND_ONCE không nhận được tin — 24/10/2026

Không gọi Zalo, không mở/dừng poller, không gửi tin, không xóa/sửa DB, không build lại trong lần kiểm tra này.

## Bằng chứng tại máy

- Danh sách Win32_Process đọc ở Windows tại thời điểm kiểm tra không có python/py hay module send_once/polling_test; có các cửa sổ cmd khác. Không có poller Python local tại thời điểm đó. Không có lịch sử đủ để loại trừ tranh sự kiện trước đó hoặc trên máy chủ khác.
- one_shot.db mở mode=ro: integrity_check=ok, deliveries=0 dòng. SHA-256 trước/sau đọc giống nhau: fe15a91e4c42ec2701857590be8961d80a10e5daea142703998e2c9a71688407. Không có one_shot_receipt.json. Mã send_once reserve/commit trước HTTP; với bản cài đặt này và DB còn nguyên, chưa đi tới lời gọi sendMessage. Không kết luận cho một bản sao khác không được kiểm tra.
- START_TEST ưu tiên py -3 còn SEND_ONCE dùng python; kiểm tra thật xác nhận cả hai cùng Python313/python.exe, Python 3.13.9, OpenSSL 3.0.18. Chưa có bằng chứng khác runtime gây lỗi.
- Hai chương trình cùng gọi polling_test.receive_one, ReadOnlyTransport và Transport.post/getUpdates, cùng base URL, POST, timeout='30', HTTP timeout=40. Không offset/cursor, không API ack riêng hoặc retry send. Token nhập riêng từng phiên, không lưu nên không thể xác minh hai lần đã nhập cùng token; getMe thành công chỉ chứng minh token lần đó được chấp nhận.

## Lỗi đã xác định từ mã

Dòng “Chưa có dữ liệu; đợi…” chỉ xuất hiện trong except APIError, không phải kết quả poll rỗng. Transport cũ ẩn cả nhóm lỗi, nên không có log để phân biệt API error code, TLS/network, timeout hoặc JSON lỗi ở lần đã qua. Không thể quy nguyên nhân gốc cho polling contention/token/mạng từ câu này.

Khác biệt xử lý: SEND_ONCE có bộ lọc accept (GROUP, người gửi không bot/self, mã thử là token tách bằng whitespace chính xác); START_TEST nhận ngay một event hợp lệ. Trước đây event không đạt lọc bị bỏ qua im lặng. Đây là một khả năng làm người dùng không biết đã nhận event; không sinh dòng “Chưa có dữ liệu” nói trên. Chưa có event/raw text/log từ lần gửi để chứng minh filter thực sự từ chối tin đúng mã. Không tự nới filter hoặc bỏ kiểm tra mã khi chưa có bằng chứng.

## Sửa tối thiểu

Giữ nguyên vòng getUpdates dùng chung, endpoint, timeout và điều kiện gửi. Thêm nhóm lỗi an toàn + mã số, đổi thông báo để không đánh đồng lỗi với rỗng, báo rõ event bị filter từ chối; ghi latest status/counters vào runtime/one_shot_poll_status.json khi có phiên do người dùng chủ động chạy. Không token/URL/ID/chat text. Không đọc/lưu lại giá trị credential hoặc tự chạy phiên mới để lấy log.

Chưa biết lỗi gốc của lần poll đã qua vì bản cũ không lưu phân loại. Chưa yêu cầu thử lại. Cần bằng chứng lỗi cũ nếu còn (ảnh/dòng CMD, không token) hoặc người dùng chủ động cho phép một phiên chỉ nhận để xác định loại lỗi; không tự thay bằng một lần send mới. Không tuyên bố bot đã gửi thành công.

Kiểm thử hồi quy: 66 unit test offline qua sau sửa, không gọi HTTP thật. Hash DB sau kiểm thử vẫn giữ nguyên, 0 dòng. Không build/đóng gói lại dự án trong lần này.
