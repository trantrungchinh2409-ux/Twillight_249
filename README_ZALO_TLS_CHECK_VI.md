# Kiểm tra riêng HTTPS/TLS Zalo trên Windows 7

Giải nén ZIP riêng vào thư mục bất kỳ rồi nhấp CHECK_ZALO_TLS_WIN7.bat. Không cần chép vào thư mục bot, không cần mở bot hay nhập token/API key. Dùng Python 3.8.10 x64 đã cài. Nếu tìm không thấy Python, chỉ nhập đường dẫn python.exe, không nhập key.

Gói chỉ đọc cấu hình proxy/CA hiện có, tra DNS và gọi HTTPS GET tới hai địa chỉ gốc công khai Google/Zalo. Không đọc kho DPAPI/runtime/DB, không import bot, không gọi nhận/gửi tin và không sửa bất kỳ chính sách Windows/SSL nào. Kết quả chỉ hiển thị trên CMD, không tự lưu log hoặc tự gửi chẩn đoán.

Gửi ảnh/copy kết quả [Zalo], [Google], ZALO_TLS_RESULT; thông tin nhạy cảm không được in. Giới hạn 5 giây tra DNS, 15 giây mỗi HTTPS request; có thể chậm thêm do cơ chế DNS/proxy hệ thống. Tôn trọng proxy đang có, không thử vượt proxy/firewall hay đổi mạng.

- HTTPS=PASS certificate=verified: đã bắt tay TLS và xác minh chứng chỉ. HTTP404 ở root Google là bình thường. Không chứng minh token/quyền bot hoặc generateContent chạy.
- category=CERTIFICATE: certificate_code 20/21 là không xác minh được issuer/chuỗi chứng chỉ; 9/10 liên quan thời hạn hoặc đồng hồ; 18/19 self-signed; 62 hostname mismatch. Không tự tải/cài CA hoặc tắt xác minh. Cần đối chiếu chứng chỉ/đồng hồ với quản trị theo mã thật.
- category=TLS_HANDSHAKE: có tls_reason kỹ thuật; chưa chắc là chứng chỉ hay firewall. Không hạ TLS để ép qua.
- category=PROXY_CONNECT proxy_http=403: proxy từ chối đường hầm; 407 yêu cầu xác thực proxy. Đây là bằng chứng từ chối ở proxy đang dùng, cần quản trị xác nhận rule/đích. Không sửa logic bot để né chặn.
- category=DNS/TIMEOUT/NETWORK: mã riêng và os_code (nếu có). Chưa đủ để kết luận do mạng công ty; có thể DNS, routing, server hoặc middlebox. Không suy ra nguồn chỉ từ timeout/reset.
- LOCAL_DNS=FAIL nhưng HTTPS=PASS có thể xảy ra khi proxy phân giải tên từ xa. Kết luận kết nối dựa vào HTTPS, không chỉ DNS cục bộ.
- HTTPS PASS nhưng HTTP_ACCESS=REJECTED: TLS đã qua, đích trả lỗi HTTP. Chưa xác định nguồn chặn hoặc quyền API; không gọi đó là lỗi SSL và không tự quy lỗi công ty.

Nếu xác nhận mạng công ty chặn API, dừng ở kết luận hạ tầng và nhờ quản trị cho phép đúng đích theo chính sách; không tiếp tục thay code nhận/gửi đang chạy tốt, không tắt WAF/TLS hoặc bảo mật toàn cục.

PAC_CONFIGURED báo có cấu hình AutoConfigURL của tài khoản Windows hay không, chỉ YES/NO/UNKNOWN, không in URL. Python urllib không chạy file PAC tự động. Nếu trình duyệt dùng PAC nhưng Python không có proxy tĩnh phù hợp, đây là khác biệt cấu hình cần quản trị xác minh; không tự đọc/chạy PAC hoặc tự đổi proxy trong bộ kiểm tra.
