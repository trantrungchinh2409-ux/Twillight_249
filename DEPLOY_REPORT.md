# JAT Design — báo cáo Cloudflare V0.1

Ngày 23/10/2026. Tiếp tục cùng repository, giữ mã Python, index.html và báo cáo Windows nguyên trạng. Đặc tả gốc được giữ nguyên tại docs/JAT_DESIGN_CLOUDFLARE_CODEX_SPEC.md. Chưa triển khai Gemini, provider, dashboard, queue hoặc quản trị.

## Gate và kết quả thật

| Gate | Bằng chứng / trạng thái |
|---|---|
| Đọc đặc tả | Đọc toàn bộ file do người dùng cung cấp |
| Zalo API/security | HTTP 200 và đọc setWebhook, getWebhookInfo, create_bot, webhook, sendMessage, hướng dẫn nhóm; kiểm tra đúng header X-Bot-Api-Secret-Token |
| Mention thật | **CHẶN**: tài liệu nhóm nói nhận cả mention lẫn quote/reply; chưa có discriminator JSON được xác minh. Không đoán mentions/entities. Parser GROUP luôn bỏ qua có lý do mention_unverified |
| Cài dependency | npm install thành công; có package-lock.json và phiên bản cố định; npm ci được kiểm tra lại trước bàn giao |
| TypeScript | npm run typecheck passed; đã sửa lỗi type TextDecoder options, kiểm tra lại passed |
| Unit / mock HTTP / SQL | **20/20 test passed**, 0 skip; SQLite thật trong Node cho SQL, mock fetch Zalo; không có tin gửi Zalo thật |
| Build | Wrangler dry-run passed; bundle khoảng 7,64 KiB, gzip 2,85 KiB. Đây không phải upload/deploy |
| D1 local | Migration 0001_state.sql đã apply thành công với Wrangler D1 local/workerd. Database UUID trong config là placeholder local |
| HTTP runtime thật cục bộ | Wrangler dev/workerd: health GET 200; webhook method sai 405; thiếu cấu hình 503; auth sai 401; PRIVATE có auth đúng 200 ignored; GROUP có auth đúng 200 mention_unverified |
| Cloudflare auth | wrangler whoami báo chưa authenticated. Không có biến CLOUDFLARE/ZALO credential khi kiểm tra tên; không đọc/in giá trị secret |
| Public deploy / workers.dev | **Chưa thực hiện**, không có URL public hoặc D1 remote. Không dùng temporary preview account để thay tài khoản người dùng |
| Zalo setWebhook/getWebhookInfo thật | Chưa gọi, chưa thay cấu hình bot đang có |
| Nhóm thật nhận phản hồi | **Chưa thử; V0.1 chưa đạt nghiệm thu** |
| ZIP | tools/package-worker.py xuất source Worker có lockfile; danh sách cho phép loại secrets, node_modules, .wrangler, DB và credential. Có SHA-256 |

## Phạm vi kiểm thử

20 test bao gồm routes/method, auth thiếu/sai, so sánh secret bằng digest, content-type, JSON lỗi, actual body quá giới hạn không dựa Content-Length, switch tắt, private, schema không rõ, GROUP fail-closed, config/token thiếu, mô hình mention nội bộ đúng/sai, nhóm ngoài allowlist, self/bot, SQL reserve unique, cooldown, TTL dọn dữ liệu, gửi thất bại không replay, lỗi storage ngăn gửi, mock POST sendMessage đúng câu cố định và kiểm tra log không có dữ liệu đầu vào.

**Positive mention là event nội bộ tổng hợp**, không phải fixture response Zalo. Test GROUP raw là negative tổng hợp và luôn từ chối. Không coi test này là proof-of-connection. Chưa kiểm thử remote D1 concurrency, callback/retry từ Zalo, CPU Workers Free hoặc gửi API thực tế. AI timeout/missing AI key không thuộc V0.1 và không được triển khai/test.

## State và retry

D1 batch transaction dọn lịch sử và reserve với unique hash event; cooldown nhóm 5 giây. State giữ tối thiểu hash ID/thời gian/status 24 giờ, không nội dung. Dọn TTL khi có eligible traffic tiếp theo, không hứa xóa đúng 24 giờ trong trạng thái idle. Sau TTL có thể chấp nhận replay cũ. Reserve-before-send ưu tiên không gửi trùng; crash/timeout có thể mất phản hồi. Không tự retry sendMessage khi kết quả không rõ. Lỗi storage trả 503; event đã reserve vẫn không gửi lại. Nếu persist kết quả lỗi sau khi send thành công, reservation còn giữ và ngăn gửi lại. Giữ giới hạn request gửi 8 giây; chưa xác minh timeout callback Zalo thực tế.

## Cloudflare Free đã đối chiếu

developers.cloudflare.com ban đầu proxy 403. Đã đọc source chính thức:

- https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/workers/platform/limits.mdx
- https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/docs/d1/platform/pricing.mdx
- https://raw.githubusercontent.com/cloudflare/cloudflare-docs/production/src/content/partials/workers/d1-pricing.mdx

Tài liệu ghi Workers Free 100.000 requests/ngày, CPU 10ms/request; D1 Free 5 triệu rows read/ngày, 100.000 rows written/ngày, 5GB tổng storage. Index/DELETE tiêu quota. Chưa xác minh gói/tài khoản thực tế; không cam kết miễn phí vô hạn. Không thêm Gemini/Queues nên không tuyên bố hạn mức của chúng.

## Cấu hình tái sử dụng và việc cần từ chủ tài khoản

Đã lưu install_script/start_skill chuyển sang npm/Worker, giữ các custom domain cũ và bổ sung api.cloudflare.com, developers.cloudflare.com, dash.cloudflare.com. Đã khai báo yêu cầu CLOUDFLARE_API_TOKEN cho api.cloudflare.com; chỉ nhập qua cài đặt bí mật an toàn, không chat. Bản nháp không tự áp dụng hoặc Publish. Không đưa token Zalo vào cấu hình cloud thay thế secret của Worker; người dùng nhập token Zalo mới và webhook secret trực tiếp trong Cloudflare dashboard khi Worker được tạo.

Cần cấp Cloudflare auth an toàn trước khi developer tạo D1 remote/deploy. Cần xác minh discriminator mention bằng tài liệu bổ sung hoặc event webhook thật đã xác thực, developer tự che dữ liệu nhạy cảm. Không yêu cầu người dùng viết code, cài dependency hoặc xử lý JSON. Chỉ khi các gate này được giải quyết mới bật gửi và nhờ người dùng thử @mention trong Zalo. Đây là điểm dừng theo điều 6 của đặc tả, không tuyên bố bot đang online.
