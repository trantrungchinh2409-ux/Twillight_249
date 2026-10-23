# JAT Design — Zalo AI Bot online (Cloudflare Workers + Gemini)

**Trạng thái:** Đặc tả để Codex triển khai. Chưa có code triển khai hay xác nhận vận hành thực tế.
**Ngày:** 2026-10-23

## 1. Bối cảnh và mục tiêu
- Zalo Bot Creator đã tạo **Bot JAT Design** (bot chính thức), và bot đã được thêm vào nhóm thử nghiệm. Thành viên đã thử `@Bot JAT Design`, nhưng bot chưa trả lời vì chưa có backend.
- Người dùng muốn bot hoạt động **online ngay cả khi tắt PC**, dùng Zalo trên web/điện thoại như bình thường. Không làm EXE Windows 7 trong phạm vi này.
- Ưu tiên **chi phí 0đ nếu trong hạn mức**, dựa trên Cloudflare Workers Free và Gemini API Free Tier (không cam kết miễn phí vô hạn).
- Bot **chỉ trả lời khi được @mention trong các nhóm được bật**; không tự động phản hồi toàn bộ tin nhắn.
- Có thể chuyển provider/model (Gemini mặc định; OpenRouter dự phòng) mà không viết lại lõi nhận tin.

## 2. Quy tắc triển khai
- BUILD-FIRST: xác minh tài liệu API -> deploy Worker tối thiểu -> thử sự kiện thật -> phản hồi cố định -> Gemini -> quản trị/cấu hình.
- Không thêm/xóa chức năng ngoài phạm vi; giữ source chia module và commit/mốc ổn định sau mỗi giai đoạn.
- Codex phải tự code, tự test và tạo artifacts trong môi trường được cấp quyền. Không đẩy việc viết code/terminal cho người dùng. Chỉ yêu cầu người dùng nhập secrets trên trang an toàn của chính họ và kiểm thử @mention trong Zalo.
- Không yêu cầu bot token, secret token hoặc Gemini API key xuất hiện trong chat, repo, ảnh chụp hoặc log.
- Không tuyên bố 'đã chạy' cho tới khi có bằng chứng deploy + request thật + gửi trả lời trong nhóm.

## 3. Kiến trúc
```text
Zalo Group --@Bot JAT Design--> Zalo Bot Webhook
  -> HTTPS Cloudflare Worker (/webhook)
  -> Verify authenticity + parse update + allowlist group + require actual mention
  -> Deduplicate event + enforce cooldown
  -> (Phase 1) fixed reply via Zalo Bot API
  -> (Phase 2) Gemini Developer API / selectable provider
  -> sendMessage to originating Zalo group
```
- Dùng **Cloudflare Workers JavaScript/TypeScript**, không dùng Python/PyInstaller, không máy chủ polling liên tục. Dùng `fetch`, `wrangler`, unit tests; giữ code dễ chuyển hosting.
- Worker có thể nhận POST và phản hồi HTTP nhanh. Nếu dùng `ctx.waitUntil` để xử lý hậu cảnh phải hiểu giới hạn thời gian; nếu thời gian gọi Gemini vượt giới hạn, cân nhắc **Cloudflare Queues / giải pháp phù hợp gói miễn phí** sau khi xác minh tính khả dụng, không tự giả định queue là miễn phí.
- State lưu trong **Cloudflare D1** hoặc storage phù hợp đã xác minh trên gói Free để chống trùng; không coi biến RAM toàn cục là kho dữ liệu bền vững. Thiết kế idempotent (ưu tiên unique event/message ID) và TTL/xóa lịch sử.

## 4. Gate kỹ thuật bắt buộc: xác minh Zalo API
Codex cần đọc tài liệu chính thức tại:
- https://docs.zaloplatforms.com/zalo-bot
- https://docs.zaloplatforms.com/docs/BOT/create_bot
- Mở liên kết tài liệu cụ thể từ trang trên cho `setWebhook`, `getWebhookInfo`, `sendMessage`, cấu trúc message/group mention và webhook security.

**Không được tự suy đoán** JSON schema, cách biểu diễn @mention, request authentication, signature, hoặc `chat_id`. Nếu tài liệu chính thức bị HTTP 403:
1. Dùng nguồn sao chép/SDK uy tín để nghiên cứu và ghi rõ nguồn + mức tin cậy.
2. Viết adapter + fixture/mock test, đánh dấu unverified.
3. Dùng một sự kiện webhook thật (được xác minh và làm sạch secrets/PII) để đối chiếu trước khi bật tự gửi.
4. Nếu không xác thực được tính toàn vẹn webhook, không triển khai public endpoint cho phép gửi tin tự động.

Chỉ chấp nhận các update group có dấu hiệu @mention **thật** đến bot theo dữ liệu API. Không mặc nhiên coi chuỗi văn bản có chứa tên bot là mention.

## 5. Phạm vi theo mốc

### V0.1 — Proof of connection (quan trọng nhất)
- Tạo repository/source TypeScript cho Cloudflare Worker.
- Endpoint health check `/health` không lộ secrets; webhook HTTPS `/webhook` POST.
- Xác thực webhook theo **cơ chế chính thức đã xác minh**. Nếu Zalo dùng secret token, kiểm tra đúng header/cơ chế tài liệu, tránh so sánh token tự đoán.
- Log an toàn chỉ gồm request ID, loại event, kết quả, error code; không log payload nhạy cảm.
- Kiểm tra bot/group ID thuộc allowlist cấu hình, và mention đúng bot; bỏ qua chat cá nhân và nhóm khác.
- Dedup/retry handling; tránh loop nếu chính bot nhắn hoặc tin đã xử lý.
- `@Bot JAT Design xin chào` -> bot gửi đúng một câu `JAT Design đã online!` trong nhóm xuất phát.
- Trường hợp tin nhắn thường, nhóm ngoài allowlist hoặc @không đúng -> không trả lời.
- Test unit/mock đầy đủ. Deploy thử lên `*.workers.dev` và dùng `setWebhook` hoặc cấu hình Zalo Bot Creator. Không khai báo hoàn tất cho tới khi có thử nghiệm thực tế.

### V0.2 — Gemini API
- Thêm module provider interface; Gemini Developer API mặc định; OpenRouter provider dự phòng, có thể chuyển bằng config không cần sửa xử lý Zalo.
- Secret lưu bằng Cloudflare secrets, không hardcode hay đưa vào client.
- System prompt bằng tiếng Việt có thể tùy chỉnh; giới hạn độ dài câu trả lời, context window/tokens, rate limit cho từng nhóm/người dùng.
- Khi Gemini lỗi 429/503: retry có backoff giới hạn; báo lỗi ngắn gọn hoặc bỏ qua theo cấu hình, không spam.
- Kiểm tra model Gemini thực sự có Free Tier của account; không mặc định mọi model đều miễn phí.
- Ghi số token (nếu API cung cấp) và ước tính chi phí; không biến ước tính thành hóa đơn chính thức.
- Giữ nguyên các phép kiểm tra @mention từ V0.1.

### V0.3 — Quản trị cơ bản (chỉ sau V0.1/V0.2 chạy thật)
- Admin page bảo vệ xác thực mạnh, cho phép bật/tắt bot, allowlist nhóm, đổi provider/model, chỉnh prompt, xem log đã ẩn PII.
- Không hiển thị lại secret API key/token dạng rõ. Chuyển đổi provider/model không cần redeploy nếu có lưu cấu hình an toàn.
- Không làm quyền năng đọc tệp người dùng, chạy shell, điều khiển thiết bị, tự gửi tin ngoài nhóm.

## 6. Bảo mật và giới hạn
- Token cũ từng hiện trên màn hình và đã được user reset: **chỉ dùng token mới**, tuyệt đối không ghi lại giá trị vào file MD/repo.
- Worker endpoint chỉ chấp nhận phương thức/kiểu dữ liệu phù hợp; xác minh chữ ký/secret theo tài liệu, giới hạn payload, chống replay/duplicate.
- Lưu tối thiểu dữ liệu tin nhắn, có thời hạn xóa; ưu tiên không lưu nội dung nhóm trong V0.1.
- Do sử dụng API AI ngoài Zalo, cân nhắc thông báo thành viên rằng tin @Bot được gửi tới bên cung cấp AI.
- Cloudflare Workers Free có giới hạn request/CPU/memory; xác minh theo tài liệu hiện thời. Gemini Free Tier áp dụng theo model, account và rate limits; host miễn phí không đồng nghĩa API miễn phí vô hạn.
- Nếu Zalo không cung cấp schema mention hoặc không xác minh được webhook thực tế thì **dừng đúng gate**, báo blocker; không khẳng định bot chạy được.

## 7. Chạy test và tiêu chí chấp nhận
- Unit: POST sai method, wrong auth, malformed JSON, private chat, group khác, tin thường, @bot đúng/sai, self-message, duplicate event, retry, lỗi AI/timeout, thiếu key.
- Integration: sandbox/mocked Zalo and Gemini HTTP; assert no secret in logs.
- Real-world acceptance: sau khi cấu hình endpoint và token mới, gửi tin thường => im lặng; `@Bot JAT Design ping` => đúng **1 phản hồi**; thử lại với nhóm khác => im lặng; thử tắt bot => im lặng.
- Thu bằng chứng triển khai: URL public đã che endpoint nếu cần, HTTP status test, timestamps và log redacted, không lộ token.

## 8. Deliverables Codex cần bàn giao
- `src/` module: entrypoint, zalo-adapter, mention-filter, dedupe, providers/gemini, config, storage, security, logger.
- `wrangler.jsonc` hoặc `wrangler.toml`, package lock, scripts test/deploy, mock fixtures, test cases.
- `.dev.vars.example` (chỉ placeholders), `.gitignore`, `.env` không commit.
- `README_VI.md` thao tác tối thiểu: tạo Cloudflare Worker, set secrets an toàn, lấy Worker URL, dán vào Webhook URL trong Zalo Creator, phép thử nhóm.
- `DEPLOY_REPORT.md`: trạng thái thực của từng gate, những gì đã/chưa được thử, chi phí/hạn mức cần lưu ý.
- Source ZIP (nếu thực sự đã xuất được), link triển khai chỉ khi thực sự deploy xong.

## 9. Hướng dẫn cho Codex khi nhận đặc tả
1. Đọc file này và hiện trạng repo. **Không tạo lại từ đầu nếu đã có code.**
2. Phân tích ngắn API/security/mention chưa xác minh, đưa kế hoạch chi tiết.
3. Build V0.1 và unit test trước; chỉ tiến tới V0.2/V0.3 sau khi user duyệt và V0.1 đủ điều kiện.
4. Nếu môi trường Codex Cloud bị 403, dùng các bản docs được người dùng đính kèm; tiếp tục mock tests và báo rõ thiếu kiểm thử API thực tế.
5. Không cần EXE, không cần Windows 7; mục tiêu là bot Zalo online chạy trên Cloudflare.

## 10. Tài liệu nguồn
- Zalo Bot overview: https://docs.zaloplatforms.com/zalo-bot
- Zalo Bot creation, long polling/webhook: https://docs.zaloplatforms.com/docs/BOT/create_bot
- Cloudflare Workers Free limits: https://developers.cloudflare.com/workers/platform/limits/
- Gemini API pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini API rate limits: https://ai.google.dev/gemini-api/docs/rate-limits
