# Zalo TLS code 19 — đối chiếu chuỗi và Windows/Python trust

`self_signed_certificate_in_chain` nghĩa là không xây được đường tin cậy tới CA đã tin tưởng. Chưa đủ để kết luận là proxy công ty: có thể TLS inspection/antivirus, CA hợp lệ của công ty chưa được cài đúng, chuỗi thiếu hoặc trust khác nhau. Không sửa code bot Windows 11.

## 1. Kiểm tra không cần token

Giải nén ZIP riêng, nhấp **CHECK_ZALO_CERT_WIN7.bat**. Không cần chạy bot hay nhập token/key. Script không đọc runtime/DPAPI/DB và không cài CA hoặc sửa registry/policy.

- `PYTHON_DEFAULT_RESULT`: TLS bằng đúng default context Python.
- `WINDOWS_STORE_READ`, các count và `CHAIN_n_SHA256`: CA Windows ROOT/CA, CA Python thực nạp và membership/fingerprint của chuỗi Windows. Membership trong store không tự chứng minh certificate được tin cho mọi mục đích; đối chiếu cả `WINDOWS_SERVER_AUTH_ELIGIBLE`/chain status.
- `WINDOWS_HTTPS`: .NET/Windows xác thực TLS và hostname mặc định, không callback bỏ qua SSL. TLS1.2 chỉ được chọn trong tiến trình kiểm tra, không đổi chính sách Windows. Có thể FAIL vì Schannel/patch/TLS khác OpenSSL; không coi mọi Windows FAIL là thiếu CA.
- `ROUTE_MATCH=YES`: route proxy/direct khai báo của Windows/Python khớp; chưa chứng minh đường vật lý/TLS inspection giống nhau tuyệt đối. `NO_OR_UNKNOWN`: có thể PAC hoặc route khác, không so trust như cùng một kết nối.
- Chuỗi thu được là **Windows xây từ chứng chỉ ServicePoint của kết nối**, có thể bổ sung intermediate/cache/root. Không gọi đây là toàn bộ chuỗi raw do server gửi trên wire. Công cụ không mở kết nối bỏ kiểm tra để lấy cert. Nếu HTTPS thất bại và Windows không cung cấp cert, báo CHAIN=UNAVAILABLE.
- Chỉ fingerprint SHA256, cờ trạng thái và mã an toàn được in. Không in subject/issuer tên nội bộ, IP, proxy URI/credential hay HTTP body. Không tự gửi hoặc lưu báo cáo. Fingerprint là định danh chứng chỉ công khai, không phải API key.

Đây là PowerShell chuẩn .NET của Windows 7; script chạy `-NoProfile -NonInteractive -File` và giữ execution policy hiện có. Nếu `POWERSHELL_POLICY_OR_RUNTIME_BLOCKED`, **không dùng ExecutionPolicy Bypass**, không đổi policy. Nhờ quản trị kiểm/cho phép hoặc ký script theo quy trình công ty. Python default TLS/store snapshot vẫn có kết quả riêng. Nếu không có chuỗi, mở đúng https://bot-api.zaloplatforms.com/ trong trình duyệt, xem Certificate/Certification Path nếu có, **không bấm bỏ qua cảnh báo để tiếp tục**. Nhờ IT đối chiếu root/issuer và SHA256; không gửi ảnh chứa thông tin công ty nhạy cảm.

## 2. Đối chiếu Windows Certificate Store với Python

Đã đối chiếu source chính thức CPython 3.8.10: khi không truyền cafile/cadata riêng, ssl.create_default_context() gọi load_default_certs(SERVER_AUTH); Windows nạp CA/ROOT phù hợp server-auth rồi các đường CA mặc định OpenSSL. Python chuẩn không tự dùng certifi của trình duyệt. SSL_CERT_FILE/SSL_CERT_DIR đang có được báo YES/NO, không in đường dẫn.

- Windows PASS, Python FAIL và route khớp: khác trust/chain hoặc TLS-client behavior cần xem fingerprint/membership; chưa được quy ngay cho proxy.
- Root được IT xác nhận là CA inspection công ty, fingerprint trong chuỗi Windows khớp: có bằng chứng cho chuỗi inspection ở kết nối Windows. Nếu root đó thiếu trong Python/default, kiểm cài ROOT/server-auth/chuỗi đúng với IT. Không suy ra chỉ dựa tên CA hoặc mã 19.
- CA public chuẩn nhưng thiếu/không hợp lệ: quản trị kiểm root/intermediate/đồng hồ và cập nhật chứng chỉ chính thức phù hợp Win7. Không tải DLL/CA ngẫu nhiên từ Internet.
- Nếu có ExplicitDistrust/NotValidForUsage/revoked: không dùng CA file để né chính sách. Dừng và nhờ IT giải quyết đúng nguyên nhân.

## 3. Phép thử CA HTTPS do quản trị phê duyệt (tùy chọn)

Chỉ làm sau khi IT xác nhận CA được phép dùng cho TLS server-auth/HTTPS inspection, kiểm tra mục đích, validity và fingerprint qua kênh độc lập:

1. IT cung cấp **chứng chỉ CA công khai** dạng PEM, không có private key, đặt tên `APPROVED_CA.pem` trong thư mục kiểm tra. Không dùng PFX/P12, không lấy leaf Zalo làm CA, không tự tạo CA và không lấy CA từ kết nối lỗi rồi tự tin tưởng.
2. Nhận SHA-256 chính xác từ IT qua kênh tin cậy độc lập. Khi chạy BAT, nhập fingerprint đó nếu đồng ý kiểm; Enter để bỏ qua. Công cụ không tự nạp CA chỉ vì có file.
3. File phải chứa đúng một certificate CA có BasicConstraints CA=true, và keyCertSign nếu khai báo KeyUsage; fingerprint sai/thiếu sẽ không chạy phép thử. Context bổ sung giữ CERT_REQUIRED, check_hostname và verify_flags như mặc định, không bật partial-chain hoặc bỏ lỗi. Chỉ thêm CA vào bộ nhớ của **phép thử**, không sửa Windows/Python/bot trust store, không set biến môi trường.
4. `APPROVED_CA_RESULT=PASS` nhưng `PYTHON_DEFAULT_RESULT=FAIL`, Exit=2: chứng minh phép thử bằng CA được chỉ định qua TLS, **chưa sửa bot**. Không bỏ qua kết quả default FAIL để chạy bot. Nếu Windows báo distrust/usage failure, không làm bước này để vượt chính sách dù có file CA.

## 4. Sửa và kiểm tra lại trước khi chạy bot

Ưu tiên IT triển khai CA đúng scope/purpose qua GPO hoặc công cụ chứng chỉ Windows được công ty duyệt. Root CA vào Trusted Root Certification Authorities, intermediate vào Intermediate Certification Authorities; không đặt leaf hoặc intermediate tùy tiện vào Root. Công cụ này không tự import. Nếu certificate không thuộc CA đã được duyệt, dừng và xác minh nguồn, không tin thêm cho đủ PASS.

Sau thay đổi do IT thực hiện, chạy lại cùng BAT, cần `PYTHON_DEFAULT_RESULT=PASS`, Exit=0. Đóng/mở lại tiến trình bot để nó nạp trust mới. Không cần sửa logic nhận/gửi, cài lại Gemini key hoặc xóa DB. Nếu Windows PASS/Python FAIL còn tiếp tục, gửi báo cáo mã/fingerprint đã lọc và route match để kiểm tra tiếp; chưa sửa bot hoặc tắt SSL.

Exit=1: chưa đạt. Exit=2: chỉ phép thử CA riêng đạt, bot/default chưa đạt. Exit=0: TLS default Zalo đạt; chưa chứng minh token, polling/sendMessage hoặc Gemini API thật hoạt động.

Nguồn:
- https://github.com/python/cpython/blob/v3.8.10/Lib/ssl.py
- https://docs.python.org/3.8/library/ssl.html#ssl.SSLContext.load_default_certs
- https://learn.microsoft.com/en-us/dotnet/api/system.net.servicepoint.certificate
- https://learn.microsoft.com/en-us/dotnet/api/system.security.cryptography.x509certificates.x509chain
