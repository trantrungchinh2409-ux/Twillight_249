# JAT Design — khóa Gemini và hạn mức trên Windows 11

## Thao tác

1. Đóng mọi cửa sổ bot/poller cũ. Giữ nguyên thư mục runtime và các database.
2. Mở SETUP_API.bat. Nhập API Key ẩn rồi Enter. Nhấn Enter để nhập khóa tiếp; gõ Y rồi Enter để hoàn tất. Khóa trùng không được lưu thêm.
3. Mở lại SETUP_API để quản lý: A thêm, D xóa, P chọn khóa chính, C kiểm tra đúng một khóa, Q thoát. Trạng thái not_checked nghĩa là đã lưu nhưng chưa xác minh với Google. C thực hiện một request tạo câu trả lời thật, có thể dùng quota; không gửi Zalo. Không tự kiểm hàng loạt.
4. Mở START_AI.bat: tự đọc các khóa đã lưu; vẫn nhập Bot Token Zalo ẩn như trước. Mặc định OFF. Chọn ON rồi gửi `@Bot JAT Design câu hỏi` trong đúng nhóm thử đã xác minh.
5. STATUS xem lượt còn lại/thời gian nghỉ. OFF ngăn bắt đầu gửi mới; ON bật lại; QUIT thoát. Request đã bắt đầu không thể thu hồi.

## Lưu khóa

Kho runtime/gemini_keys.dpapi được Windows DPAPI mã hóa toàn bộ, gắn với tài khoản Windows hiện tại. Chỉ dữ liệu đã mã hóa được ghi đĩa, có đọc kiểm lại trước khi thay tệp. Không hiển thị khóa, không lưu plaintext vào cấu hình/log/source/ZIP. Không đặt khóa vào SYSTEM_PROMPT.txt. Giữ kín tài khoản Windows và bản sao runtime; DPAPI không thay thế bảo vệ tài khoản.

SETUP_API và START_AI khóa độc quyền kho trong suốt phiên. Đóng START_AI trước khi thêm/xóa/chọn khóa. Đổi máy hoặc tài khoản Windows cần nhập lại khóa; ZIP source không mang theo kho hoặc dữ liệu nhóm.

Khóa dự phòng chỉ dùng sau lỗi xác thực/lỗi riêng của khóa chính đã xác định. Không đổi khóa với 429, lỗi thanh toán, lỗi mạng, model 404 hoặc lỗi quyền chung. Khóa đã đánh dấu invalid_key được bỏ qua cho đến khi kiểm tra lại bằng C hoặc thay khóa. Không xoay tài khoản để né hạn mức Google, vốn áp dụng theo dự án.

## Hạn mức và an toàn

- Ngân sách chung cho bot/nhóm thử, không nhân lên theo số khóa: tối đa 10 lượt gọi AI trong cửa sổ trượt 120 giây. Lượt lỗi cũng tính bảo thủ để tránh gọi vượt giới hạn. Lượt thứ 10 bắt đầu nghỉ 300 giây; không tự OFF, hết thời gian nhận tin mới bình thường.
- Trong thời gian nghỉ, ở tin khớp bộ lọc kế tiếp sau cooldown 10 giây, gửi đúng một thông báo: "JAT Design đã hết lượt sử dụng tạm thời. Vui lòng thử lại sau 5 phút." Không gọi Gemini, không xếp hàng trả lời những tin đã bỏ qua. Không có tin phù hợp thì không chủ động gửi thông báo. Thời gian nghỉ tính từ lượt thứ 10.
- Bộ đếm, thời điểm mở lại, dấu đã thông báo, cooldown và trạng thái gửi được ghi bền trong runtime/ai_reply.db. Đóng/mở không reset. Giữ nguyên bảng cũ, không xóa database. Bản mới thay giới hạn thử 3 lượt bằng chính sách trên.
- Google 429: chờ Retry-After hoặc RetryInfo dài nhất; thiếu chỉ dẫn thì chờ tăng dần 60 giây đến tối đa 1 giờ. Thời gian Google được lưu cả trong kho và DB, áp dụng mọi khóa. Không gửi thông báo hết hạn mức nội bộ để thay thế lỗi Google, không yêu cầu nạp tiền trong nhóm. Tin bị 429 không tự gửi lại; tin mới sau thời gian chờ mới được xử lý.
- Lỗi khóa/thanh toán/provider hiển thị loại và mã an toàn trong CMD, rồi dừng để kiểm tra. Không in response lỗi thô có thể chứa bí mật.
- Giữ cooldown 10 giây, chống trùng, bỏ tin cũ trước ON, bỏ tin của bot và giới hạn đúng nhóm đã xác minh. Lọc đúng chuỗi `@Bot JAT Design`, không tuyên bố xác thực mention entity.
- Trước sendMessage ghi dấu gửi bền. Timeout/mất xác nhận: khóa gửi tiếp và dừng; không tự thử lại hoặc tự xóa khóa. Giữ DB và báo kết quả cho Codex.

## AI và bản ổn định

Giữ Gemini 3.5 Flash-Lite, URL/version và adapter getUpdates/sendMessage đã hoạt động. START_AI dùng lớp quản lý mới; các chương trình cũ còn nguyên. Không tự gọi Gemini khi khởi động. Kiểm tra thực bằng C là tùy chọn cho đúng khóa đã chọn.

Giữ SYSTEM_PROMPT.txt ngắn, không thêm câu hỏi chào mời; maxOutputTokens=128, 1–2 câu/tối đa 50 từ, chỉ câu hỏi hiện tại, không lịch sử nhóm. START_AUTO.bat, SEND_ONCE.bat, parser/poller/transport và one_shot.db được giữ nguyên. Mỗi thời điểm chỉ chạy một bot với cùng token; khóa tiến trình Windows ngăn poller trùng trong cùng phiên đăng nhập. Chưa triển khai Railway; kho DPAPI này dành cho Windows, không dùng trực tiếp trên Linux.

Nhánh phát triển: jat-design/api-vault-and-limits, xuất phát bản stable AI. Không sửa nhánh stable hoặc Railway. Khi giải nén để nâng cấp máy đang chạy, giữ runtime hiện tại; không thay bằng DB từ bản cũ và không chạy song song hai thư mục.

## Bằng chứng kiểm thử

Các bài kiểm thử dùng khóa/sự kiện giả, DPAPI thật trên Windows và tiến trình Python mới để xác minh giải mã sau khởi động lại. Kiểm tra nhiều khóa/trùng/xóa/chọn chính; giới hạn/cửa sổ trượt/nghỉ/thông báo một lần; trạng thái qua restart; 429 không chuyển khóa; timeout Zalo không gửi lại. Xem VALIDATION_API_LIMITS.md để biết kết quả cuối.

Mốc AI cũ đã được chủ dự án xác nhận trả lời thật ngày 24/10/2026. Bản quản lý khóa/hạn mức mới chưa gọi Google bằng khóa thật hoặc gửi Zalo thật trong đợt kiểm thử kỹ thuật này. Không suy ra thành công thực tế từ unit test. Không tạo tài nguyên hoặc kích hoạt gói trả phí.
