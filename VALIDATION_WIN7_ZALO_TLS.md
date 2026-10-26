# Kiểm chứng tích hợp Zalo-only G3 — 26/10/2026

Nhánh phát triển: `jat-design/win7-zalo-rootg3-20261026`. Kế thừa source `61a1a3d` và bản launcher Python38 đã bàn giao `e37f39e`; không sửa stable, không build EXE, không chạy lại GitHub Actions.

## Chứng chỉ đóng sẵn

Root G3 lấy từ kho CA tin cậy có sẵn của môi trường; DER SHA256 khớp đúng pin người dùng đã xác minh:
`31AD6648F8104138C738F39EA4320133393E3A18CC02296EF97C2AC9EF6731D0`.
Không lấy từ kết nối TLS thất bại, không tạo CA, không tuyên bố tải DigiCert mới. `certs/PROVENANCE.json` ghi nguồn và metadata. Không cần intermediate vì người dùng đã đo thực tế T2 root-only PASS.

Lệnh kiểm độc lập:
```
openssl verify -x509_strict -check_ss_sig -no-CApath -no-CAstore -CAfile certs/DigiCertGlobalRootG3.pem certs/DigiCertGlobalRootG3.pem
```
Kết quả `OK`: root tự ký hợp lệ, CA/constraints/thời hạn được OpenSSL kiểm tra, chỉ dùng CA file đã pin. TLS chain/hostname Zalo thật trong bản tích hợp chưa được đo tại môi trường công ty; không thay kết quả đó bằng unit test.

## Test offline thực hiện tại môi trường Linux

```
PYTHONPATH=tests python3 -m unittest test_core test_official_api test_auto_reply test_send_once test_gemini test_managed_limits test_https_probe test_win7_console test_win7_python test_zalo_tls_standalone test_zalo_cert_check test_digicert_bundle test_zalo_ca_config test_failover_portable.ReconnectTests -v
```

130 test: **127 đạt, 3 bỏ qua** vì cần Windows/native CA bundle. Test tích hợp mới dùng root thật được đóng gói, không gọi API hoặc dùng key/token thật. Kiểm pin/root/hostname flags, context chỉ tin root G3, CA thiếu/hỏng/ghép thêm hoặc đồng hồ quá hạn phải dừng, không tạo opener/fallback, Gemini giữ default handler/trust, diagnostic dùng hai context khác nhau. Regression nhận/gửi và lỗi HTTP/API/TLS, Gemini, 10 AI/120 giây, nghỉ 300 giây, cooldown, dedup, uncertain-send guard, reconnect và console đều đạt trong các test phù hợp Linux.

Đã kiểm CRC/hash từng file trong manifest ZIP, parse Python theo cú pháp 3.8, BAT ASCII/CRLF, giải nén vào đường dẫn có dấu cách và `!`, dựng Zalo Transport với root trong ZIP và dựng Gemini bằng default trust khi chặn mọi kết nối mạng. Xóa CA khỏi bản giải nén: dừng trước khi tạo opener. Không có runtime, profile, DB, key/token thật, EXE/DLL trong ZIP. Không có CA downloader nào được gọi bởi install/start/preflight/Zalo transport.

So sánh với `e37f39e`: các module Gemini, key vault, managed AI, managed limits, state, polling, reconnect, portable profile, webhook switch, setup API và SYSTEM_PROMPT không thay đổi. Trong official_api chỉ đổi cách tạo opener, phần request/response/parser giữ nguyên. Thêm zalo_tls, cập nhật diagnostic/preflight/packaging và BAT trỏ CA riêng.

## Chưa kiểm chứng lại ở phiên này

- Không có Windows7/Windows CryptoAPI/DPAPI thật tại môi trường Linux; không giả lập encryption rồi tuyên bố native DPAPI PASS. Các bài vault/failover/profile phụ thuộc native Windows không được tính vào 127 test đạt. Code của các phần này được giữ nguyên.
- Python thực thi test tại đây không phải CPython3.8.10; đã kiểm cú pháp3.8. Native3.8.10 trên Win7 và SQLite/DPAPI đã được người dùng xác nhận trước đây, cần preflight có sẵn ở máy đích cho bản ZIP này.
- Người dùng đã xác nhận Win7 T1 mặc định FAIL19, T2 rootG3 PASS, T3 root+intermediate PASS, T4 Google PASS, exit0. Đây là bằng chứng thực tế cho lựa chọn root-only, chưa phải xác nhận đã chạy bot với bản tích hợp mới.
- Không gọi Zalo/Gemini live, không gửi tin; không kiểm CRL/OCSP online và không tuyên bố revocation PASS. Không tắt bất kỳ xác minh SSL/hostname hay policy Windows nào.
