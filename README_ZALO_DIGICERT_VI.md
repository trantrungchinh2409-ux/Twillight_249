# Win7 Zalo — DigiCert Global Root G3 + RapidSSL TLS ECC CA G1

Bộ kiểm tra độc lập, không cần token/key, không chạy bot và không sửa Windows Certificate Store hoặc source Windows11. ZIP này **không đóng sẵn chứng chỉ**. Lần chạy đầu, Python tải CA qua HTTPS có xác minh từ DigiCert chính thức. Nếu không tải hoặc xác minh được, công cụ dừng FAIL; không lấy CA từ kết nối lỗi hay trang sao chép. Root bắt buộc có SHA256:

31AD6648F8104138C738F39EA4320133393E3A18CC02296EF97C2AC9EF6731D0

## Cách chạy

Giải nén **toàn bộ ZIP vào thư mục riêng**, nhấp **CHECK_ZALO_DIGICERT_WIN7.bat**. Dùng Python 3.8.10 x64 đã cài; không cài pip, EXE, DLL hoặc CA. Nếu không tự tìm thấy Python, nhập đường dẫn python.exe, không phải token.

CA được lưu riêng trong thư mục `ca_digicert` cạnh BAT, không cài vào Windows. Cần quyền ghi thư mục đã giải nén. Không giải nén vào thư mục bot đang chạy. Khi có SOURCE.json, công cụ dùng lại file nhưng kiểm pin/chữ ký mỗi lần; nếu file hỏng sẽ FAIL, không tự tin file hỏng.

Nguồn tải đầu tiên:
- Root: https://cacerts.digicert.com/DigiCertGlobalRootG3.crt
- Intermediate: https://cacerts.digicert.com/RapidSSLTLSECCCAG1.crt

Nếu intermediate không hợp lệ/không tải được, công cụ chỉ tra hai trang danh mục HTTPS chính thức của DigiCert để tìm liên kết `cacerts.digicert.com`; chỉ chấp nhận đúng subject, issuer, thời hạn và chữ ký. Giới hạn dung lượng, timeout và số liên kết; không chuyển HTTP hoặc mirror. Fingerprint root được chốt trước, không lấy fingerprint từ file vừa tải để tự tin nó.

Nếu Win7 không xác minh được HTTPS của chính DigiCert, công cụ dừng. Không thể dùng CA chưa tải/xác minh để tự sửa kết nối tải chính nó. Gửi mã category/certificate_code cho IT; không tắt SSL hoặc nhập CA lạ.

Các phép kiểm:
1. Đọc root và intermediate công khai trong ca_digicert; kiểm root pin, intermediate hash/subject/issuer, thời hạn và chữ ký root tự ký/intermediate do root cấp bằng Windows CryptoAPI trong bộ nhớ. Không dựa tên file để tin cậy CA. SOURCE.json ghi URL DigiCert chính thức, hash và metadata.
2. DEFAULT_ZALO: trust mặc định của Python; báo root G3 có được nạp hay không.
3. PRIVATE_ROOT_ONLY: context riêng chỉ tin root G3 đã pin, không dùng Windows Store.
4. PRIVATE_ROOT_PLUS_INTERMEDIATE: context riêng root + RapidSSL intermediate đã xác minh. Không bật partial-chain; OpenSSL vẫn phải xây chain tới root, kiểm chữ ký/thời hạn/basic constraints/server purpose và hostname/SNI thật bot-api.zaloplatforms.com. Không follow redirect, không đọc body hoặc gửi message.
5. Chỉ sau full bundle PASS: thử cách tích hợp bằng SSL_CERT_FILE trong **tiến trình chẩn đoán**, tạo default Python context mới rồi kiểm lại Zalo và Google. Biến môi trường được phục hồi ngay; không setx, không sửa launcher/bot và không lưu cấu hình hệ thống.

HTTP404 ở địa chỉ gốc có thể là TLS PASS; không chứng minh quyền bot. Công cụ chỉ in mã lỗi đã lọc và fingerprint kỹ thuật, không in exception chứa proxy/credential.

## Đọc kết quả

- DEFAULT FAIL nhưng ROOT_ONLY PASS, root không có trong default: phù hợp thiếu root G3 trong trust Python. Dữ liệu certutil Missing Issuer hỗ trợ chẩn đoán, không phải lý do tắt SSL.
- ROOT_ONLY FAIL nhưng ROOT_PLUS_INTERMEDIATE PASS: có vấn đề intermediate hoặc lựa chọn chain; bundle đầy đủ giải quyết trong context riêng. Không tự kết luận server luôn thiếu intermediate vì có thể khác chuỗi/route/cache.
- ROOT_PLUS_INTERMEDIATE FAIL: xem category/certificate_code. 19/20/21 còn lại có thể chuỗi khác, proxy/antivirus TLS inspection, thiếu CA khác hoặc route khác. Không thêm CA lạ để ép PASS. Timeout/proxy/DNS được phân loại riêng.
- Root/hash/signature/time FAIL: dừng, giữ file để đối chiếu; kiểm nguồn/fingerprint/đồng hồ hoặc crypto support của Win7 với quản trị. Không sửa checksum hoặc bỏ kiểm chữ ký.
- PROCESS_ONLY_INTEGRATION_TEST=PASS: đã chứng minh default Python context mới với CA file process-only xác minh được Zalo và Google trong phép kiểm này. **Chưa khởi động/thử bot thật.**

Exit0: full bundle + thử context tích hợp Zalo/Google đều PASS. Exit1: file/crypto hoặc TLS FAIL. Exit2: full TLS PASS nhưng context tích hợp chưa đạt. Gửi ảnh kết quả đã lọc, không gửi token/key.

## Revocation và chain

Chữ ký root/intermediate được kiểm offline. TLS thật kiểm toàn đường xác thực tới root và hostname bằng OpenSSL. **CRL/OCSP không được kiểm trong phép thử Python mặc định này**; không tuyên bố revocation PASS, không tắt revocation hay thay chính sách Windows. Nếu certutil/IT báo certificate revoked, không chạy bot dù phép thử TLS OpenSSL PASS. Nếu báo CRYPT_E_REVOCATION_OFFLINE hoặc revocation unknown, quản trị cần kiểm CRL/OCSP/AIA của issuer theo SOURCE.json; không tắt kiểm tra để né lỗi. Root/intermediate fingerprint khớp không thay thế kiểm tra thu hồi online.

## Tích hợp sau khi máy Win7 thật PASS

Không cần đổi code nhận/gửi, Gemini, DPAPI, DB hoặc hạn mức. Phương án tối thiểu là launcher riêng đặt SSL_CERT_FILE trỏ bundle đã xác minh trong setlocal của CMD rồi gọi START_WIN7_PYTHON.bat hiện có; không setx, không import CA Windows, không thay Python toàn máy. CPython3.8 tạo default context sẽ nạp Windows CA phù hợp server-auth và CA file này. Chỉ triển khai launcher đó sau khi xem báo cáo PASS tại máy công ty và được người dùng duyệt dùng CA bundle; bản kiểm tra hiện tại **không** tự chạy hoặc sửa bot.

Nếu private bundle vẫn FAIL thì dừng tích hợp, chẩn đoán đúng lỗi còn lại. Không build lại EXE hoặc sửa logic bot đang chạy trên Windows11.

## Tình trạng bàn giao 26/10/2026 — không chạy lại CI

Lần CI cuối: https://github.com/trantrungchinh2409-ux/Twillight_249/actions/runs/40297807016/job/121488041263

Step 4 có tên gộp “Fetch official HTTPS, pin root, verify public CA signatures”, exit 1. BUILD_STATUS.json ghi `stage=tests`: lệnh tải và xác minh CA đã exit 0, lỗi phát sinh tại `python -m unittest test_digicert_bundle -v`, không có URL tải nào được chứng minh là lỗi trong lần này. Log chi tiết yêu cầu đăng nhập GitHub; chưa xác định test/traceback cụ thể. Không kết luận DigiCert chặn tải hay tự retry CI. Bản ZIP này được tạo cục bộ từ mã kiểm tra, không phụ thuộc CI hay chứng chỉ đã đóng gói.

Các bài unit test độc lập chạy được trên Linux được ghi tại VALIDATION_WIN7_PYTHON.md trên GitHub; test mock chỉ kiểm hành vi fail-closed, không chứng minh TLS thật. Chưa chạy BAT/CryptoAPI trên máy Win7 công ty, chưa kiểm chain live/CRL/OCSP ở đó. Chỉ kết quả thực tế khi chạy BAT mới quyết định PASS/FAIL cho máy này.
