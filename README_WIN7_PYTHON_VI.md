# JAT Design — chạy bằng Python 3.8 trên Windows 7

Tiếp tục source `jat-design/failover-win7-portable` tại `61a1a3d`, không dùng EXE cũ. Cần **Python 3.8.10 x64 đầy đủ** đã cài trên Windows 7 Professional SP1 x64. Không dùng Python embeddable thiếu module. SQLite cần là module trong Python (`sqlite3`/`_sqlite3`), không chỉ chương trình sqlite3.exe bên ngoài.

## Cách chạy bằng chuột

1. Đóng bot cũ trên mọi máy. Giải nén toàn bộ ZIP vào thư mục có quyền ghi, ví dụ `D:\JATDesign`. Không chạy BAT ngay trong ZIP và không chỉ chép riêng BAT.
2. Nhấp **INSTALL_WIN7.bat**. Script tự tìm đúng Python 3.8.10 x64 qua đường dẫn đã nhớ, launcher `py -3.8`, vị trí cài phổ biến và PATH. Nếu chưa tìm thấy, nhập đường dẫn python.exe đã cài (không phải EXE bot). Không cần quyền quản trị, không chạy pip, không cài lại Python hay SQLite.
3. Bộ kiểm tra offline xác minh SQLite từ đúng Python, ghi database tạm, DPAPI theo tài khoản Windows, mutex và TLS. Không gọi API hoặc gửi tin. Nếu báo lỗi, giữ nguyên runtime và báo mã lỗi; không chép DLL lạ, không tắt TLS.
4. Menu cài đặt: `1` thêm/quản lý nhiều Gemini Key bằng nhập ẩn; `2` nhập hồ sơ nhóm đã xác minh; `3` xuất hồ sơ từ runtime cũ; `4` kiểm HTTPS không credential (tùy chọn); `Q` kết thúc. Mục kiểm một key trong trình quản lý có gọi Gemini và dùng quota; thêm/lưu key không kiểm hàng loạt.
5. Nhấp **START_WIN7_PYTHON.bat**. Nhập token Zalo ẩn khi được hỏi. Bot mặc định **OFF**, kiểm trạng thái webhook và nhóm đã duyệt trước. Gõ `ON` để nhận tin mới; `STATUS` xem trạng thái; `OFF` tạm dừng; `QUIT` dừng hẳn.

## Hồ sơ cũ và chống gửi lặp

- Nếu nâng cấp ngay trong cùng thư mục/cùng tài khoản Windows, giữ **nguyên runtime/**. ZIP không chứa runtime và không xóa/ghi đè DB, kho DPAPI hoặc bộ đếm. Luôn đóng bot trước khi giải nén cập nhật.
- Nếu chuyển thư mục, dùng menu `3` xuất hồ sơ riêng từ runtime cũ rồi menu `2` nhập vào thư mục mới. Đích có dữ liệu sẽ bị từ chối, không ghi đè. Hồ sơ riêng chứa ID nhóm, chỉ giữ tại máy của bạn, không gửi GitHub/chat. Không chạy hai bản song song.
- DPAPI gắn với tài khoản/máy Windows. Chuyển từ máy khác phải xuất hồ sơ trên máy nguồn bằng đúng tài khoản, nhập hồ sơ trên máy đích và nhập lại Gemini Key. Không chép kho gemini_keys.dpapi giữa máy/tài khoản khác.
- Nếu chỉ có bản EXE cũ bị lỗi SQLite nhưng còn runtime, chạy bản source trên cùng máy/tài khoản để dùng menu xuất hồ sơ. Không cần chạy EXE. Nếu không còn hồ sơ nhóm/biên nhận đã xác minh, bot sẽ dừng; không tự học nhóm lạ hoặc bỏ cổng duyệt.
- Nếu Zalo còn webhook bật, bot dừng và không tự xóa webhook. Báo trạng thái để xử lý theo quy trình hiện có; không chạy polling đồng thời với bot khác.

## Giữ nguyên chức năng

Không sửa Gemini/model/prompt, Zalo polling, kho nhiều key DPAPI, failover đúng loại lỗi, 10 lượt AI/120 giây, nghỉ 300 giây, cooldown 10 giây, trạng thái qua restart hoặc chống trùng. 429 không chuyển key để né quota. Gửi không rõ kết quả vẫn khóa chống gửi lại, không tự phát lại tin. Không ghi key/token/câu hỏi/câu trả lời vào log.

Khóa màn hình không chủ động dừng Python; máy vẫn phải thức và có mạng. Không sửa sleep policy, proxy, firewall, chứng chỉ hoặc bảo mật công ty. Lỗi TLS/proxy phải xử lý với quản trị, không tắt xác minh chứng chỉ.

`INSTALL_WIN7.bat` chỉ kiểm tra/chuẩn bị và nhớ đường dẫn Python trong runtime/python38.path. Runtime chỉ dùng thư viện chuẩn; requirements-build.txt/PyInstaller không cần cho bản này. Không kèm Python, EXE, DLL hay profile riêng trong ZIP.

## Mức kiểm chứng

Xem VALIDATION_WIN7_PYTHON.md. Không có máy Windows 7 tại môi trường Codex; kiểm tra Windows CI mới hơn không thay thế nghiệm thu Windows 7 SP1 tại công ty. Sau kiểm tra offline, cần một lần chạy thực trên máy của bạn để xác nhận DPAPI, SQLite, TLS/mạng công ty và Zalo/Gemini thật. Không nhập token/key vào GitHub hoặc chat.

## Bản sửa console khi chọn mục 1 bị thoát (mã 120)

Launcher mới tự bật hiển thị ASCII/không dấu trên Windows 7. Chỉ đổi cách hiển thị thông báo và prompt CMD; không đổi dữ liệu nhập, API key, đường dẫn, prompt Gemini, nội dung Zalo hoặc dữ liệu DPAPI. Nhập key vẫn dùng getpass, không cho rơi về chế độ hiện key. Không cần đổi registry, font, chứng chỉ hoặc cài lại Python.

Đóng CMD bot/cài đặt cũ. Giải nén bản cập nhật đè file chương trình trong **cùng thư mục hiện tại**, giữ nguyên runtime, rồi chạy lại INSTALL_WIN7.bat → 1. ZIP không chứa runtime nên không ghi đè kho/DB. Nếu vẫn lỗi, chỉ gửi các dòng báo lỗi kỹ thuật; không gửi key/token hoặc file runtime.
