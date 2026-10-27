# Agent Win7 — bằng chứng kiểm thử và giới hạn nghiệm thu

Ngày27/10/2026; nhánh `jat-design/agent-win7-20261027`, base `8dcb83e` (source/ZIP Win7 đã xác nhận tại `53f5976`). Không sửa stable, không đổi file bot cũ. Gói bổ sung không có runtime/one_shot.db/vault hoặc profile giả. Không build EXE, không chạy CI, không deploy webhook/Railway.

## Phân biệt tính năng và bằng chứng

| Chức năng | Code/test offline | Cần thử thật |
| --- | --- | --- |
| Tên theo ID thật + manager xác nhận | Có; challenge nonce chỉ đọc, chống trùng alias/đổi nhầm ID, lưu qua restart | Gán7 tên tại máy công ty bằng event Zalo thật |
| Phiên theo bot/group/sender, không trộn | Có; ba thành viên xen kẽ, nhiều group/bot độc lập | Kiểm thực tế tài khoản/nhóm hiện dùng |
| Hỏi tiếp không @ dựa sender_id | Có, FOLLOWUP mặc định OFF; quản lý phải xác nhận bật | Zalo có chuyển plain event qua getUpdates hay không; không thể dùng code ép API giao thêm tin |
| Reply trực tiếp vào bot | Runtime chưa có adapter đã xác minh; raw field không được đoán | Cần hợp đồng/mẫu Reply xác thực để bật; không phụ thuộc logic sender-session ở trên |
| Nhận diện đang nói người khác | Mặc định chỉ @; gate normalized evidence có test cho tương lai | Chưa có metadata runtime đáng tin; opt-in plain có rủi ro chen ngang, phải dừng phiên/tắt FOLLOWUP khi cần |
| 6 cặp hội thoại, TTL5 phút, DPAPI SQLite | Có; test double cho logic Linux, native test được chuẩn bị | DPAPI/native Python3.8.10 của Agent cần SELF_TEST tại Win7 |
| Delay2.5s, polling không chặn | Có; clock giả và worker model bị giữ trong khi caller tiếp tục nhận/queue | Latency thật phụ thuộc Gemini/mạng/cooldown, không hứa2–3s khi bị giới hạn |
| Typing chính thức | Đã đọc tài liệu, có POST sendChatAction/action typing và test payload | Chưa gọi token thật; cần nhìn UI và STATUS typing_api_last |
| OFF/cancel/dedup/uncertain/10 lượt/nghỉ5 phút | Có; regression reuse engine cũ, không nới budget; 429 không đổi key | Không tạo timeout/spam thật để thử; chưa chạy native integration tại máy người dùng |
| Rollback | Không thay core/BAT cũ; dùng lại cùng DB/vault/counters, test bảo toàn state | Đóng Agent trước rồi chạy ROLLBACK_WIN7.bat |

## Căn cứ API đọc lại

HTTP200 ngày27/10/2026 tại:
- https://docs.zaloplatforms.com/docs/BOT/best-practices/build-bot-interaction-with-group
- https://docs.zaloplatforms.com/docs/BOT/apis/getUpdates
- https://docs.zaloplatforms.com/docs/BOT/apis/sendMessage
- https://docs.zaloplatforms.com/docs/BOT/webhook
- https://docs.zaloplatforms.com/docs/BOT/apis/sendChatAction

Typing: tài liệu ghi POST tới sendChatAction, body chat_id/action='typing', response {ok:true}. Một request best-effort/turn sau khi đã có budget; timeout2s, không retry, không gửi placeholder. Các kết quả HTTP trên là đọc docs, không phải Bot API live bằng token.

Group guide mô tả @ và Reply là các đường nhận. Mẫu trong source chưa có field Reply/target đủ xác minh. Sender/group có thể lấy trực tiếp từ event như bot cũ; do đó FOLLOWUP theo sender được triển khai độc lập theo yêu cầu mới, nhưng nhận plain event là cổng nghiệm thu nền tảng. Không tự suy từ message_type/text hoặc tự thêm API ngoài tài liệu.

## Kiểm thử đã thực hiện

Lệnh suite offline:
```
PYTHONPATH=tests python3 -m unittest test_agent_win7 test_local_group_profile test_core test_official_api test_auto_reply test_send_once test_gemini test_managed_limits test_https_probe test_win7_console test_win7_python test_zalo_tls_standalone test_zalo_cert_check test_digicert_bundle test_zalo_ca_config test_failover_portable.ReconnectTests -v
```

**184 test: 179 PASS, 5 SKIP; 0 failures/errors** tại môi trường Linux, không phải máy Win7. Agent riêng có34 test:33 PASS/1 SKIP native DPAPI. Các bài native/hạ tầng Windows khác không được giả chạy hoặc tính đạt. Phiên chuẩn bị không có API key/token thật, không gửi chat/typing thật.

Phủ các ca: ba người hỏi xen kẽ và tên đúng ID; session history/cặp6/expiry/restart; người không có phiên; self/private/wrong-group; FOLLOWUP OFF mặc định, xác nhận bật, hỏi tiếp qua sender dù không có Reply metadata; normalized Reply vào bot và Reply người khác chỉ trong fixture; per-user pending; delay nhanh/chậm; OFF khi model/chờ/ON lại/đổi Agent; clear/end scoped/dedupe; timeout gửi persistent; shared10th slot/pause; Gemini429/failover không né quota; API typing; nonce+quản lý xác minh tên; giữ one_shot.db; base hash/rollback.

Test fake crypto được đánh dấu TESTONLY, chỉ nằm trong tests, không có công tắc production chuyển sang crypto giả. Runtime dùng DPAPI có sẵn của Windows. Test adapter Reply nhận normalized_test_reply_to_bot là fixture, **không phải field Zalo được công nhận**, không có CLI bật adapter này.

## Kiểm tra gói và bảo toàn source

AGENT_BASELINE.json chứa hash của file core/BAT/prompt/CA mốc cũ. Packager so sánh source hiện tại với hash và cấm add-on chứa tên file trùng baseline. Entrypoint cũng kiểm base trước khi import/chạy bot; thiếu/sai base trả60, không sửa file.

ZIP chỉ chứa file Agent mới. CRC/hash manifest được đọc lại, Python parse cú pháp3.8, BAT ASCII/CRLF. Kiểm thử cài overlay trong thư mục tạm có dấu cách/ký tự đặc biệt trên source base, so sánh hash trước/sau, chạy lại các bài Agent offline với socket bị chặn. Profile/vault/runtime cá nhân không có trong ZIP. Không thay SYSTEM_PROMPT, getUpdates/sendMessage, Gemini/model/HTTP cũ, TLS G3, DPAPI, key pool, managed limits, dedup/uncertain, one_shot.db hoặc START_WIN7_PYTHON.bat.

Rollback không khôi phục DB cũ hoặc tạo lại ngân sách; chỉ gọi runner cũ với cùng runtime. Agent không phát lại hàng đợi sau restart; event đang xử lý đã được ledger cũ reserve bền vững. Timeout gửi thật giữ guard, chỉ hủy đã chứng minh chưa gọi HTTP mới được gỡ marker tạm của chính nó.

## Chưa được tuyên bố

Chưa chạy Agent live trên Windows7/Python3.8.10, chưa bind ID của7 người thật, chưa biết plain messages được API giao, chưa kiểm UI typing, chưa chứng nhận Reply metadata. Parse3.8 không thay native execution. TLS G3 và bản base là bản người dùng đã nghiệm thu trước đây; không vì thế tuyên bố Agent mới đã live PASS.

Chỉ yêu cầu tester thử từng bước sau offline PASS như README; không spam/không ép timeout thật/không dùng mock để tuyên bố thành công live.

## Toàn suite và Python3.8.10 — lượt xác minh cuối

Đã chạy toàn suite tại Linux/Python3.12.14:252 test,200 PASS,6 SKIP,45 errors do Windows DPAPI không có và1 failure ở luồng mutex Windows. Đây là kết quả môi trường, không được ghi thành toàn suite PASS. Nguồn Python3.8.10 từ python.org không tải được trong container (URLError), không tắt HTTPS để tải.

Theo ưu tiên kiểm tra toàn bộ test trên Python3.8.10, chuẩn bị **một lượt Windows runner x64** với socket bị chặn, không cấp key/token ứng dụng và không gọi API live. Kết quả sẽ nằm tại AGENT_NATIVE_TEST_REPORT.json; chỉ công bố PASS khi báo cáo thực có PASS. Workflow không fetch CA, không deploy và không tự retry; chỉ chạy khi chính file workflow thay đổi. Các commit tài liệu/ZIP sau đó dùng skip ci.


## Kết quả native thực tế — PASS

Một lượt đã hoàn thành tại https://github.com/trantrungchinh2409-ux/Twillight_249/actions/runs/40447607982/job/122002496979 . Báo cáo tự ghi tại AGENT_NATIVE_TEST_REPORT.json:

- Windows Server2022 build20348, **CPython3.8.10 x64**.
- **252 test chạy,251 PASS,1 SKIP,0 failures,0 errors**.
- Test skip: test_official_bundle_real_pins_native_signatures_and_dates, cần full root+intermediate môi trường riêng. Test root G3 thực tế và context chỉ dùng root vẫn PASS.
- Native DPAPI của Agent và các test base/vault/startup/mutex đã chạy trên Windows. Socket bị chặn toàn suite. Không có app key/token, không gọi Zalo/Gemini/typing live.
- Chạy một lần, không retry workflow. Commit report/final ZIP dùng skip ci và không đổi workflow để chạy lại.

Kết quả này thay trạng thái “native pending” ở mục trên; không thay đổi các giới hạn live Win7/Zalo đã ghi. Đây là kiểm interpreter3.8.10/native Windows, chưa phải chạy Agent thật trên Windows7 ở công ty. Không có sửa code runtime sau lượt native PASS; chỉ cập nhật tài liệu/báo cáo/allowlist đóng gói.
