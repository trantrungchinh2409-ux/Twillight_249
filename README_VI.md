# JAT Design — Cloudflare Workers V0.1

Đây là hướng triển khai hiện tại trong cùng kho Twillight_249. Mã Python, trang HTML và báo cáo Windows được giữ làm lịch sử; không tiếp tục yêu cầu EXE/Windows 7. Không thêm Gemini, OpenRouter, providers hay dashboard trong V0.1.

**Chưa deploy online; chưa đạt nghiệm thu mention thật.** Worker có xác thực webhook chính thức nhưng vẫn khóa mọi GROUP vì thiếu schema phân biệt mention và quote/reply. Không bật gửi dựa vào chuỗi tên bot hoặc tự suy đoán field `mentions`.

## Thành phần

`src/index.ts`: route health/webhook; `security.ts`: header secret, body tối đa 64 KiB; `zalo-adapter.ts`: parser và POST sendMessage; `mention-filter.ts`: bộ lọc nội bộ; `dedupe.ts`, `storage.ts`: D1 chống trùng/cooldown; `config.ts`, `logger.ts`: cấu hình và log tối thiểu. Không log token, payload, text hoặc group ID. Observability tự động đang tắt.

Xác thực dùng đúng `X-Bot-Api-Secret-Token` theo tài liệu Zalo, secret 8–256 ký tự. Health chỉ chứng minh endpoint trả lời, không chứng minh bot sẵn sàng.

D1 lưu SHA-256 của khóa bot/group/event, timestamp và trạng thái. Reserve trước khi gửi, không retry gửi khi timeout/kết quả chưa rõ. Chấp nhận khả năng mất phản hồi khi crash, không khẳng định exactly-once. Cooldown nhóm 5 giây; dọn dữ liệu hết hạn 24 giờ khi có sự kiện đủ điều kiện tiếp theo (không đảm bảo xóa theo đồng hồ nếu không có traffic). Sau TTL, replay cũ có thể được chấp nhận; chưa có timestamp/replay window thật được xác minh. Không lưu nội dung nhóm.

## Developer tự thực hiện

Node 24.19.0, npm lockfile. `npm ci`, `npm run typecheck`, `npm test`, `npm run build` (dry-run, không publish), `npm run db:local`, `npm run dev`. CI `.github/workflows/worker.yml` chỉ test/build và tải artifact, không deploy. Không cần người dùng chạy terminal hoặc cài dependency.

Để deploy, developer cần Cloudflare authentication được cấp an toàn, tạo D1, thay UUID placeholder trong wrangler.jsonc bằng database_id thật, chạy migration remote và deploy Worker khi BOT_ENABLED vẫn false. UUID toàn số 0 hiện tại chỉ phục vụ build/local, không phải DB đã được tạo trên tài khoản.

## Thao tác tối thiểu phía chủ tài khoản

1. Cấp quyền Cloudflare qua cơ chế an toàn; không gửi API token qua chat. Developer xử lý tạo Worker/D1 và các lệnh triển khai.
2. Khi Worker đã tồn tại, vào Cloudflare dashboard → Worker → Settings → Variables and Secrets, nhập mới `ZALO_BOT_TOKEN` và `ZALO_WEBHOOK_SECRET` dưới dạng secret. Chỉ dùng token Zalo mới đã reset. Không gửi ảnh chứa giá trị.
3. Developer cấu hình BOT_ID và ALLOWED_GROUP_IDS (JSON array), xác minh metadata mention, triển khai parser, rồi mới bật BOT_ENABLED. Không coi metadata nội bộ trong test là sự kiện thật.
4. Sau khi có URL workers.dev thật, nhập URL kết thúc `/webhook` trong Zalo Creator và cấu hình cùng webhook secret qua giao diện an toàn nếu có; nếu không, developer dùng setWebhook/getWebhookInfo từ môi trường có secret an toàn. Chưa gọi các API đổi webhook trong phiên này.
5. Người dùng thử tin thường (im lặng), @Bot đúng (đúng một câu `JAT Design đã online!`), nhóm không cho phép (im lặng), tắt bot (im lặng). Developer ghi kết quả và tự che dữ liệu nếu thu fixture thật.

Chưa có Worker URL công khai để bàn giao. Cần giữ nguyên cổng mention trước khi gửi tự động.

## Nguồn và chi phí

Zalo: docs.zaloplatforms.com/docs/BOT/apis/setWebhook, /getWebhookInfo, /sendMessage; /docs/BOT/webhook; /docs/BOT/best-practices/build-bot-interaction-with-group. Hướng dẫn nhóm xác nhận nhận cả mention và reply, chưa đưa field phân biệt.

Tài liệu Cloudflare trên developers.cloudflare.com bị proxy 403; đã đọc source chính thức repository cloudflare/cloudflare-docs nhánh production: workers/platform/limits.mdx, d1/platform/pricing.mdx và partial workers/d1-pricing.mdx. Workers Free: 100.000 request/ngày, 10 ms CPU/request; D1 Free: 5 triệu rows read/ngày, 100.000 rows written/ngày, 5 GB tổng storage. Index và DELETE cũng tiêu quota. Đây là hạn mức tài liệu, không phải cam kết tài khoản thực tế hoặc miễn phí vô hạn. CPU production chưa benchmark. Không dùng Queue/AI. V0.1 chờ gửi cố định tối đa 8 giây thay vì giao việc không bền vào RAM/waitUntil.

Xem DEPLOY_REPORT.md cho bằng chứng đã/chưa kiểm thử.
