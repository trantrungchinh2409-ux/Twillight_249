# JAT Design Win7 — Python 3.8.10, sửa khởi tạo 26/10/2026

Bản source, không EXE, không cần pip hoặc tải DLL. Dùng đúng Python 3.8.10 x64 đã cài tại công ty. Giữ TLS G3 riêng cho Zalo, không đổi trust Gemini/Windows. Chưa xác nhận bot thật trên Win7 với bản sửa mới.

## Thao tác ngắn

1. Đóng mọi bot/poller ở cả hai máy. Sao lưu thư mục bot cũ nguyên vẹn bằng cách sao chép; không xóa runtime. Giải nén toàn bộ bản sửa, không chạy từ ZIP. Có thể cập nhật source trong thư mục cũ để giữ đúng runtime của cùng tài khoản Win7; ZIP sạch không chứa runtime và không được dùng lệnh xóa thư mục cũ.
2. Mở INSTALL_WIN7.bat để chọn đúng Python 3.8.10 nếu chưa nhớ đường dẫn. Menu1 nhập khóa, menu2 nhập hồ sơ, menu3 xuất hồ sơ, menu4 kiểm HTTPS, Q thoát. Các dòng OK ENV chỉ kiểm môi trường, chưa có nghĩa bot đủ hồ sơ.
3. Chạy CHECK_WIN7.bat. Công cụ không hỏi token và không gọi API; nó kiểm prompt, kho thật, hồ sơ/biên nhận/DB AI, DPAPI và quyền ghi. Nếu thiếu hồ sơ sẽ báo E33/E36/E43; làm bước Chuyển hồ sơ dưới đây. Nếu E31, chạy SETUP_API.bat. Nếu E32, giữ kho cũ; kiểm đúng tài khoản và tệp, không tự xóa kho.
4. Khi CHECK PASS, chọn mục4 của INSTALL để kiểm HTTPS không credential. Google root HTTP404 có thể là TLS PASS; cần Zalo/Google đều xác minh chứng chỉ được. SELF_TEST_WIN7.bat kiểm SQLite/CA/DPAPI/mutex/logic bằng dữ liệu giả; PASS tự kiểm không thay thế CHECK kho/hồ sơ thật.
5. Chạy START_WIN7_PYTHON.bat, nhập token Zalo ẩn. Bot đối chiếu đúng bot với biên nhận cũ, kiểm webhook, mặc định OFF. Chọn ON và thử một câu trong đúng nhóm. Không chạy bot Win11 cùng lúc. Nếu lỗi, chỉ gửi mã E/stage hoặc mã API trong CMD, không gửi token/key/runtime.

## Chuyển hồ sơ nhóm đã xác minh — bắt buộc nếu máy Win7 chưa có

Không cần lấy ID nhóm bằng tay. Không tạo one_shot.db rỗng và không tắt guard.

- Trên máy Win11 đang có bản đã gửi tin thành công: dừng bot, giải nén source sửa vào thư mục riêng; chạy EXPORT_PROFILE_WIN7.bat và nhập đường dẫn thư mục runtime của bản đang dùng. Chỉ đọc runtime nguồn. Công cụ xuất runtime/transfer-profile-private.zip trong thư mục source sửa.
- Chép riêng hồ sơ đó sang Win7. Nó chứa ID nhóm/bot hash, biên nhận, DB hạn mức/chống trùng, không chứa token hoặc Gemini key. Giữ riêng, không đưa vào GitHub/chat/ZIP công khai.
- Trên Win7 chạy INIT_PROFILE_WIN7.bat, chọn tệp vừa chuyển. Công cụ nhập mẫu nhóm, mã hóa lại DPAPI theo tài khoản đích và giữ nguyên DB AI. Kho gemini_keys.dpapi sẵn có ở Win7 được giữ nguyên. Không chép kho DPAPI Win11 sang Win7.
- Nếu đã có DB/mẫu nhóm ở đích, công cụ từ chối ghi đè. Không xóa chúng để ép nhập; giữ bản sao và gửi mã từ CHECK để xử lý có kiểm soát. Nếu có profile-import.pending hoặc trạng thái gửi chưa rõ, dừng và giữ nguyên.
- CHECK lại rồi mới chạy START. Khi quay lại máy cũ sau khi đã dùng máy mới, phải chuyển trạng thái mới theo quy trình; không dùng DB cũ để reset hạn mức.

## Mã lỗi chính

| Mã | Ý nghĩa / thao tác |
|---|---|
|20|Không tìm đúng Python 3.8.10 x64; mở INSTALL chọn python.exe.|
|21/22|Môi trường SQLite hoặc DPAPI/CA/import chưa đạt; giữ dữ liệu, không tải DLL lạ.|
|E30|Prompt thiếu/hỏng; dùng lại SYSTEM_PROMPT đúng bản.|
|E31/E32|Chưa có khóa hoặc không đọc/giải mã được kho; SETUP trên đúng máy/tài khoản, không xóa kho cũ.|
|E33–E38|Thiếu/hỏng DB biên nhận hoặc hồ sơ nhóm, hoặc sai bot. Dùng hồ sơ đã xác minh; không tự nhập group ID.|
|E39|Runtime không có quyền ghi. Dùng thư mục có quyền ghi, không đổi bảo mật công ty.|
|E40|Nhập hồ sơ dang dở; giữ marker/DB và báo Codex.|
|E41/E42|Không lấy được mutex kho/bot; đóng SETUP/poller khác trong cùng phiên Windows.|
|E43/E44|Thiếu/hỏng/khóa DB AI, không tạo DB rỗng để reset.|
|E45|Gửi chưa rõ kết quả từ phiên trước; không tự gửi lại.|
|E46–E49|Lỗi khởi tạo khác/token/transport/DB; gửi mã và stage an toàn.|
|ZALO_API|Giữ nguyên kind và mã HTTP/API, không kết luận token sai từ TLS.|

Kiểm tra kho chỉ chứng minh giải mã được, không chứng minh quyền/quota Gemini. Kiểm tra hồ sơ offline chưa đối chiếu token cho đến lúc getMe. Không có truy vấn getUpdates hoặc sendMessage trong CHECK/SELFTEST. TLS hostname verification vẫn bật, không sửa chứng chỉ hệ thống, proxy, firewall hoặc webhook. Hạn mức 10/120 giây, nghỉ300, cooldown10, failover và uncertain-send guard giữ nguyên.
