# Kiểm chứng sửa startup — 26/10/2026

Bản dựa commit765218065fed0e7e854b37cedbf2bc49f9fcd4d0, nhánh Python3.8+G3. Không build EXE.

Kết quả cuối được ghi trong OUTPUT_VERIFICATION.json kèm bản bàn giao. Kiểm thử trên Windows11 với CPython3.8.10 x64, SQLite3.35.5 và DPAPI native; không gọi API credential, không gửi Zalo. Các ca sai tài khoản DPAPI được mô phỏng lỗi giải mã, không tuyên bố đã thử tài khoản Windows thứ hai.

Các ca mới: hồ sơ hợp lệ không thay byte DB/kho; thiếu/sai schema/hỏng/khóa DB; thiếu receipt/sample/DB AI; sai bot; DPAPI hỏng; kho thiếu/rỗng/hỏng; import dang dở; uncertain-send; lỗi quyền; mutex; mock startup đi tới bảng ON/OFF; export/import và restart giữ dedup. Có kiểm tra BAT thật và ZIP giải nén với đường dẫn có khoảng trắng/ký tự đặc biệt.

Baseline175 test có một fixture HTTPError không có body gây KeyError khi close trên Python3.8; sửa fixture bằng BytesIO rỗng. Không sửa logic TLS để né lỗi test. Giữ nguyên core Zalo/getUpdates/sendMessage/Gemini/model/prompt/vault/limits/dedup, CA G3, profile import/export. Chỉ đổi kiểm tra startup, hướng dẫn và launcher; mã lỗi installer được bảo toàn.

Chưa có stack trace gốc từ Win7 để kết luận nguyên nhân duy nhất của lần lỗi cũ. Thiếu hồ sơ đã được tái hiện và được báo cụ thể; các nguyên nhân còn lại sẽ có stage/code. Chưa thử bản sửa này với tin Zalo thật trên Win7; đây là bản ứng viên chờ nghiệm thu máy công ty. Không thay webhook, không Railway hoặc gói trả phí.

Kết quả cuối Python3.8.10: 198 bài, 197 PASS, 1 SKIP (kiểm official full bundle/native signature cần root+intermediate môi trường riêng), 0 lỗi. Root G3 đóng kèm vẫn được kiểm pin/context riêng. Thử ngoài đích Python3.13: 192 PASS, 2 SKIP, 1 failure + 3 errors ở TLS vì default partial-chain; không sửa phần TLS đã chạy được trên3.8.10 và không tuyên bố hỗ trợ3.13.
