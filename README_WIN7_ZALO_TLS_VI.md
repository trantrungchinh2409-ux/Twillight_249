# JAT Design Win7 — tích hợp root G3 riêng cho Zalo

Đây là bản Python 3.8.10 x64 của source hiện có, không có EXE mới. Root DigiCert Global Root G3 được đóng sẵn: **không tải CA khi cài hoặc chạy**. Chỉ thay cấu hình HTTPS của Zalo; không thay logic bot, Gemini, API vault, DPAPI, hạn mức, failover hoặc chống trùng.

## Chạy bằng chuột

1. Đóng mọi bản bot cũ. Giải nén **toàn bộ** ZIP, không chạy BAT bên trong ZIP. Nếu cập nhật tại cùng thư mục và tài khoản Windows: giữ nguyên `runtime/`, không xóa database hoặc kho key. ZIP không chứa runtime.
2. Nhấp **INSTALL_WIN7.bat**. Bộ kiểm tra offline xác minh Python 3.8.10 x64, SQLite, root CA, DPAPI và source trước. Không cần pip hoặc quyền quản trị.
3. Mục `1` quản lý Gemini API Key bằng nhập ẩn. Mục `4` kiểm HTTPS Zalo/Google không cần key/token; Zalo dùng root riêng, Google dùng trust mặc định. HTTP404 ở URL gốc vẫn có thể là TLS PASS. `Q` thoát menu.
4. Nhấp **START_WIN7_PYTHON.bat**. Token Zalo được nhập ẩn theo luồng cũ; bot mặc định OFF, chỉ bật ON theo luồng đã có sau khi các kiểm tra nhóm/webhook đạt. Không cung cấp key/token trên GitHub/chat.

Nhóm đã duyệt, receipt và DPAPI vẫn là điều kiện bắt buộc. Nếu dùng thư mục mới, chuyển hồ sơ bằng menu xuất/nhập hiện có trong README_WIN7_PYTHON_VI.md; không bỏ cổng duyệt và không chạy hai bản song song. Chuyển máy/tài khoản phải nhập lại key theo luồng DPAPI cũ.

## Phạm vi TLS

Hai BAT đặt biến `JAT_ZALO_CA_FILE` trỏ đúng `certs/DigiCertGlobalRootG3.pem` trong `setlocal`, chỉ cho tiến trình được khởi chạy. `Transport` Zalo tạo HTTPSHandler với context riêng: CERT_REQUIRED, check_hostname, SNI, không partial-chain, không follow redirect. Không cài CA vào Windows, không setx, không sửa proxy/chính sách Windows, không thay global SSL context hoặc SSL_CERT_FILE. Gemini giữ nguyên opener/default trust như bản cũ. Khi không có biến này, đường chạy cũ (bao gồm Windows11) dùng HTTPS mặc định như trước.

CA được kiểm lại khi preflight và tạo Zalo transport: chỉ đúng root với fingerprint DER SHA256

`31AD6648F8104138C738F39EA4320133393E3A18CC02296EF97C2AC9EF6731D0`

File thiếu, hỏng, bị ghép thêm chứng chỉ, sai fingerprint hoặc đồng hồ/thời hạn không hợp lệ: dừng an toàn, không rơi về kết nối không xác minh. Không sửa checksum hay bỏ verify để ép chạy.

Chỉ đóng root G3: bạn đã xác nhận T2 root-only và T3 root+intermediate PASS trên Win7. Không có lý do thêm intermediate vào trust. OpenSSL vẫn phải xây và xác minh chain máy chủ Zalo tới root đã pin, kiểm hostname, thời hạn và mục đích server-auth. Nếu server thay đổi chain sau này và TLS không đạt, dừng để chẩn đoán, không tự thêm CA lạ.

## Nguồn và giới hạn kiểm chứng

Root lấy từ kho CA tin cậy có sẵn của môi trường thực thi; **DER trùng chính xác fingerprint root chính thức bạn đã xác minh**, không phải chứng chỉ trích từ kết nối TLS lỗi. Không tuyên bố đã tải mới từ DigiCert. `certs/PROVENANCE.json` ghi nguồn, fingerprint, thời hạn và lệnh OpenSSL kiểm chữ ký tự ký đạt. URL tham chiếu chính thức: https://cacerts.digicert.com/DigiCertGlobalRootG3.crt .

Đã chạy test offline cho pin, CA lỗi, cách ly Gemini/Zalo, no-fallback và regression logic hiện có; xem VALIDATION_WIN7_ZALO_TLS.md. Không dùng mock để tuyên bố TLS thật PASS. Kết quả live T1–T4 tại máy công ty do bạn cung cấp; bản tích hợp này chưa chạy bot thật bằng key/token của bạn. Không có key/token/DB/profile riêng trong ZIP.

TLS Python mặc định không kiểm CRL/OCSP online: không tuyên bố revocation PASS, không thay chính sách hoặc tắt kiểm tra nào của Windows. Nếu IT báo chứng chỉ bị thu hồi, dừng dùng và xử lý với IT.
