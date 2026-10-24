# Railway — bản chuẩn bị, CHƯA TRIỂN KHAI

Ngày kiểm tra: 24/10/2026. Railway connector đã đăng nhập đúng tài khoản chủ dự án, list_projects trả 0 project. Công cụ không cung cấp billing/subscription: **chưa xác minh gói tài khoản, thẻ, credit hoặc giá tài khoản riêng**. Không tạo project/service/volume, không sửa Variables, không đăng ký gói hay deploy.

## Mốc bảo toàn

GitHub jat-design/stable-ai-20261024 và JAT-Design-AI-stable-20261024.zip được tạo trước sửa prompt/cloud. Biên nhận Windows xác nhận AI sent lúc 15:34:39 UTC+7, model3.5 Flash-Lite; chủ dự án nhìn thấy tin. Giữ nguyên code Windows nhận/gửi/AI; SYSTEM_PROMPT mới bỏ câu mời hỗ trợ thêm, giữ 1–2 câu/50 từ và maxOutputTokens128. Prompt đọc khi mở lại phiên, không cập nhật vào phiên đang chạy.

## Đề xuất cấu hình cụ thể

| Mục | Chuẩn bị |
|---|---|
| Source | Nhánh jat-design/railway-preparation, Dockerfile Python3.13-slim |
| Start | python -m jat_design.cloud_worker, không dùng launcher .bat |
| Số poller | 1 replica, 1 region, không cron, không deployment preview/autodeploy |
| Trạng thái | BOT_ENABLED=false mặc định, chưa gọi API khi OFF |
| Khóa cùng cloud | flock độc quyền trên volume /data/polling.lock; không block được laptop khác |
| Cutover | LOCAL_POLLERS_STOPPED=true chỉ sau kiểm tra mọi poller Windows đã thoát |
| Lưu trữ | Volume /data; ai_reply.db bền, guard/dedup/cooldown/quota không reset |
| Secrets | ZALO_BOT_TOKEN, GEMINI_API_KEY, ZALO_GROUP_ID; không Git/log |
| Kiểm bot | EXPECTED_BOT_ID_SHA256 lấy từ bản one-shot đã thành công, so với getMe |
| Restart | ON_FAILURE, tối đa3; lỗi API/cấu hình tạo hold bền, lần khởi động lại không gọi API |
| Rollout | overlapSeconds=0, drain90s; khóa volume bảo vệ trường hợp 2 process chồng |
| Sleep | TẮT Serverless trong dashboard; không cấu hình trường không được schema xác nhận |
| RAM/CPU dự kiến | Giới hạn RAM512MiB, CPU0.25vCPU trước; đo thực sau smoke test |
| Public URL | Không cần cho polling; không mở domain/port/healthcheck HTTP giả |

Adapter Linux chỉ thay cách nhập secret, chọn nhóm, khóa tiến trình và signal; tái sử dụng Transport, OfficialAPI, Gemini, AIForwarder và AutoResponder đã chạy. Không cố giải mã DPAPI Windows trên Linux. Các giá trị bot/group sẽ được lấy từ dữ liệu local đã xác minh qua công cụ an toàn lúc chuẩn bị Variables; chủ dự án chỉ nhập token/key trong ô Secret, không phải tự viết code hoặc gõ JSON.

Docker chưa có trên môi trường Windows hiện tại nên **chưa build/chạy container hoặc kiểm flock Linux thật**. Đã test local các cổng OFF, bắt buộc xác nhận dừng local, bắt buộc volume và hold trước API; không thay bằng kết luận Linux production đã đạt. Cần container smoke test trước deploy trả phí.

## Giới hạn phiên cloud đầu

Giữ giới hạn thử AI 3 lượt bền. Không âm thầm bỏ giới hạn để gọi đó là bot24/7. Khi chuyển: dừng local, dùng SQLite backup sau khi tiến trình thoát để mang ai_reply.db hiện tại sang /data; nếu đã dùng1/3 thì cloud chỉ còn2/3. Đủ quota hoặc kết quả chưa rõ sẽ giữ OFF, không tự reset qua restart. Trước production cần chủ dự án duyệt ngân sách/phản hồi theo ngày và thay trial cap có kiểm thử riêng. Đây là bước nghiệm thu cloud, chưa phải cấu hình production trả lời vô hạn.

## Chi phí công khai đã đối chiếu

Railway Hobby tối thiểu **5USD/tháng**, gồm5USD usage; không tính máy móc thành5USD + usage từ đồng đầu tiên. Phần vượt credit tính thêm. RAM10USD/GB-tháng, CPU20USD/vCPU-tháng, egress0.05USD/GB, volume0.15USD/GB-tháng.

Ví dụ giả định (chưa đo): RAM trung bình0.125–0.25GB, CPU0.02–0.05vCPU, volume0.5GB, egress1GB/tháng => tài nguyên khoảng1.78–3.63USD/tháng, nằm trong5USD Hobby. Nếu RAM thực0.5GB và CPU0.05vCPU thì khoảng6.13USD/tháng. Đây là ước tính, không phải trần chi phí; cân nhắc ngân sách Railway5–8USD/tháng cho bot nhỏ, chưa thuế/tỷ giá/Gemini. Free1USD credit/tháng/Trial5USD một lần không đảm bảo chạy24/7 dài hạn.

Gemini3.5 Flash-Lite Standard: input0.30USD/triệu token, output2.50USD/triệu token (kể cả thinking). Giả định500input +128output cho mỗi lượt: khoảng0.00047USD/lượt, 1000 lượt khoảng0.47USD. Nếu prompt dài hơn/thinking hoặc request test bổ sung, tính lại theo usage thực. Không gửi history/tools/grounding. Free tier có quota, không cam kết khóa của chủ dự án miễn phí.

Đề xuất cảnh báo/giới hạn chi phí Railway phải được chủ dự án duyệt: hard limit có thể dừng toàn bộ workload workspace, ảnh hưởng uptime và các project khác sau này. Không tự bật. Gemini quota/Google Cloud budget là phần riêng; giới hạn Railway không khóa hóa đơn Google. Dừng3lượt hiện tại giữ chi phí thử nhỏ.

Nguồn: https://docs.railway.com/pricing/plans ; https://docs.railway.com/pricing/cost-control ; https://docs.railway.com/deployments/serverless ; https://docs.railway.com/volumes ; https://docs.railway.com/config-as-code/reference ; https://ai.google.dev/gemini-api/docs/pricing .

## Quy trình chuyển duy nhất một poller

1. Chủ dự án duyệt gói/chi phí cụ thể; xác minh billing thực. Không thực hiện bước tạo tài nguyên trước duyệt.
2. Build và smoke test container offline; tạo service OFF, một replica/region, tắt autodeploy/Serverless, mount volume và nạp Secrets an toàn.
3. Windows OFF/QUIT, chờ request đang chạy xong. Kiểm OS không còn START_AI/START_AUTO/poller khác. Không chỉ dựa vào cửa sổ hiển thị OFF.
4. Backup SQLite đúng lúc dừng; mang trạng thái và quota sang volume. Không đưa bản sao DB vào Git/ZIP public.
5. Xác nhận local đã dừng rồi mới đặt BOT_ENABLED=true và LOCAL_POLLERS_STOPPED=true cho cloud. Kiểm getMe, webhook tắt, Gemini test riêng; chỉ một cloud lease giữ lock.
6. Người dùng thử một câu, xác minh tin thật và DB. Tắt laptop để kiểm không phụ thuộc máy. Theo dõi24giờ với giới hạn ngân sách đã duyệt; trial3 hiện tại phải được giải quyết trước tuyên bố production24/7.
7. Rollback: cloudOFF/stop, chờ process/lease giải phóng, chuyển DB cloud mới nhất về đúng local nếu cần; chỉ sau đó bật Windows. Không mở hai bên để so sánh bằng traffic thật. Giữ Worker Cloudflare nguyên; webhook vẫn off khi polling.

Chưa có dịch vụ Railway thật hoặc bảo đảm24/7 ở thời điểm báo cáo.
