# Kiểm chứng hồ sơ nhóm trực tiếp Win7 — 27/10/2026

## Source và phạm vi

Base: `19b041e7714b0ccc1cf1f3445ce5b055afeaa108`, nhánh `jat-design/win7-python38-startup-fix-20261026`, là bản có CHECK_WIN7/E33 người dùng đang chạy. Nhánh phát triển mới: `jat-design/win7-local-group-profile-20261027`. Không sửa stable, không merge hoặc deploy, không build EXE, không chạy GitHub Actions.

Bổ sung local_group_profile, BAT VERIFY_GROUP_WIN7 và chế độ launcher --verify-group. Reader startup/verified_group chấp nhận bằng chứng receive-only riêng, không làm giả api_acknowledged của đường legacy. Các yêu cầu receipt cũ vẫn giữ cho hồ sơ legacy.

Các module managed_ai, managed_limits, key_vault, gemini_client, official_api, polling_test, reconnect, state, portable_profile, webhook_switch, root G3 và SYSTEM_PROMPT không đổi so với base. Trong auto_reply chỉ thêm nhánh đọc hồ sơ mới; engine gửi/giới hạn không thay đổi. Schema trạng thái AI dùng lại chính State/ManagedResponder hiện có.

## Căn cứ API

Đọc lại https://docs.zaloplatforms.com/docs/BOT/apis/getUpdates thành công HTTP200 ngày27/10/2026. Công cụ chỉ dùng getMe/getWebhookInfo/getUpdates qua ReadOnlyTransport sẵn có; không đổi webhook, không gửi tin. Sự kiện GROUP thực tế từ các phiên cũ đã được source hỗ trợ ở tầng quan sát; phép khởi tạo mới vẫn yêu cầu nhận live nonce, đúng loại GROUP, sender non-bot, timestamp hợp lệ và người dùng xác nhận.

Không tuyên bố đã xác minh mention entity; bộ lọc text/mention của bot hiện tại không đổi. Không có token để gọi API live ở môi trường này.

## Kiểm thử offline

Lệnh đã chạy:
```
PYTHONPATH=tests python3 -m unittest test_local_group_profile test_core test_official_api test_auto_reply test_send_once test_gemini test_managed_limits test_https_probe test_win7_console test_win7_python test_zalo_tls_standalone test_zalo_cert_check test_digicert_bundle test_zalo_ca_config test_failover_portable.ReconnectTests -v
```

**150 test: 146 PASS, 4 SKIP; 0 failures/errors.** Các skip cần Windows/native CA môi trường riêng. Báo cáo máy/Python tại LOCAL_GROUP_VERIFICATION.json. Không chạy toàn suite native Windows trên Linux rồi tuyên bố DPAPI hoạt động.

Test mới kiểm:

- Luồng launcher không yêu cầu ready/profile trước khi vào khởi tạo; input chuyển hướng không đọc token.
- getMe/getWebhookInfo/getUpdates đi qua wrapper chỉ đọc; sendMessage/setWebhook/deleteWebhook/testWebhook bị từ chối.
- API lỗi đầu tiên, webhook bật, timeout, marker sai, PRIVATE, bot/self sender, timestamp sai/NaN/future, người dùng hủy: không tạo hồ sơ.
- Nhận nonce + xác nhận tạo đúng schema, receipt receive-only riêng, không có api_acknowledged giả, không lưu sender/text/raw event/nonce nguyên văn.
- Reader restart, CHECK và verified_group đọc lại, đối chiếu bot; đổi DB/proof, sai bot hoặc pending phải chặn. Xóa proof không biến receipt receive-only thành receipt legacy.
- Không ghi đè hồ sơ đã tồn tại, không né uncertain-send, lỗi giữa chừng giữ pending để CHECK/START chặn.
- Dedup/counters/cooldown/Google waits và byte vault còn lại được bảo toàn; nghỉ mới ít nhất5 phút, không nới pause có sẵn. Verification event được reserve consumed trong ledger AI.
- Luồng legacy vẫn đọc được theo điều kiện cũ; regression API/Gemini/limits/dedup không đổi.

**DPAPI trong các test Linux là test double có nhãn TESTONLY, chỉ dùng thư mục tạm.** Nó không phải mã hóa thật, không được sử dụng trong production và không được coi là bằng chứng nhóm thật. Code production chỉ gọi Windows CryptProtectData/CryptUnprotectData hiện có; trước ghi phải encrypt/decrypt readback đạt. Có test native DPAPI mới nhưng tại môi trường này được skip.

## Kiểm tra artifact

ZIP allowlist source và CA công khai; không glob runtime, không chứa hồ sơ mới, database, Gemini keys, token, EXE hoặc DLL. CRC và mọi hash trong SOURCE_MANIFEST được đọc lại kiểm; tất cả Python parse cú pháp3.8. BAT ASCII/CRLF và chỉ gọi đúng --verify-group. Giải nén vào đường dẫn có dấu cách/ký tự đặc biệt, chạy test hồ sơ mới từ bản giải nén, chặn toàn bộ kết nối mạng và dùng test DPAPI double; không dựa import từ checkout ngoài ZIP.

Các lệnh tải CA không được gọi; root G3 đã đóng sẵn, TLS Zalo/Gemini giữ cấu hình đã xác nhận. Báo cáo OUTPUT_VERIFICATION.json/VALIDATION_STARTUP_FIX.md cũ vẫn là bằng chứng lịch sử của base19b041e, không phải kết quả native Windows của bản khởi tạo mới này.

## Còn phải nghiệm thu trên Win7 thật

Chưa chạy CMD BAT, CPython3.8.10 hoặc DPAPI native của bản mới tại máy người dùng; đã kiểm cú pháp3.8 và logic offline, không thay native execution bằng parse. Chưa gọi API live bằng token thật, chưa có nonce/event/nhóm thật của phiên này, chưa chứng minh quyền gửi hoặc Gemini quota. Người dùng đã báo Win7 Python/SQLite/TLS/vault PASS trước khi yêu cầu khởi tạo.

Chỉ sau READY tại máy Win7 → người dùng gửi nonce trong nhóm thử → RECEIVED GROUP → XAC NHAN → PASS LOCAL PROFILE → CHECK PASS READY, mới mở START và tự bật ON theo luồng cũ. Bot không gửi trong công cụ xác minh. Thiếu lịch sử từ máy nhà được ghi rõ là không khôi phục; pause mới5 phút chỉ là biện pháp thận trọng, không tái tạo dữ liệu đã mất. Mọi dữ liệu còn trên Win7 được giữ nguyên.
