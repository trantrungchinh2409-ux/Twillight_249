# Kiểm chứng bản Python Windows 7 — 26/10/2026

Base GitHub: jat-design/failover-win7-portable, 61a1a3d9884938736ee83a762e3cdf10cc570105.
Nhánh phát triển mới: jat-design/win7-python38-launchers-20261026. Không thay nhánh stable.

Đã kiểm tra dependency: runtime hoàn toàn thư viện chuẩn. Không cần pip/PyInstaller; SQLite/DPAPI lấy từ Python 3.8.10 x64 đã cài và Windows. Lỗi _sqlite3 của EXE cũ không được sửa bằng việc thay DLL; launcher bỏ qua EXE và kiểm đúng module từ Python.

Thêm launcher/check/menu/package; không sửa các module Gemini, polling, key vault, hạn mức, dedup, profile, prompt đã có. Công việc Cloudflare chưa commit được bảo toàn ở Git stash trước khi chuyển nhánh.

Kiểm thử Linux: bộ test gốc 130 có các lỗi Windows-only (DPAPI/mutex), một failure vì platform guard và một skip; không coi đó là kiểm chứng native Windows hoặc tự mock DPAPI để tuyên bố đạt. Các test đa nền tảng và test mới được chạy riêng, ghi kết quả thực trong báo cáo bàn giao. GitHub Actions mới chạy toàn bộ suite, self-test DPAPI và kiểm launcher bằng CPython 3.8.10 x64 trên windows-2022. Trạng thái job phải đọc được mới được tuyên bố Windows CI đạt; việc lưu workflow không đồng nghĩa đã chạy.

ZIP theo allowlist, có CRC/readback/SHA-256 và SOURCE_MANIFEST.json; không bao gồm runtime, token/key, DB, profile riêng, .git, EXE/DLL, node_modules hoặc .venv. Đây là source để chạy trực tiếp, không phải EXE hoặc chứng nhận tương thích Windows 7.

Chưa nghiệm thu trên máy Windows 7 SP1 thật; không có cuộc gọi Gemini/Zalo thật trong lần sửa này. Cần người dùng chạy INSTALL rồi START trên máy đích. Không thay đổi mạng, chứng chỉ, webhook hoặc dịch vụ Cloudflare đang có.

Kết quả tại môi trường Codex: suite đa nền tảng được chọn chạy 93 test, 92 passed và 1 native-Windows skipped, không lỗi. Sáu test launcher riêng: 5 passed, 1 native-Windows skipped. Đã đối chiếu diff: các module lõi được liệt kê ở trên và SYSTEM_PROMPT.txt hoàn toàn không đổi. ZIP đã kiểm CRC và SHA-256 từng thành phần; không kèm file bí mật hoặc DB. Không coi các skip Windows là passed.

Windows CI đã xác minh thành công cho source commit 84541268f3bdeef2f83ff0a6522176d247e6288a:
https://github.com/trantrungchinh2409-ux/Twillight_249/actions/runs/40256072444
Job windows-python38: checkout, Python3.8.10 x64, toàn bộ suite, self-test DPAPI/SQLite/limits/failover và source launcher, đóng gói, upload artifact đều success. Tổng suite source có 136 test; hai decorator skip đều áp dụng chỉ khi không phải Windows/Python3.8.10 x64. Không có kết quả live Gemini/Zalo. GitHub public log chi tiết không truy cập được (404); kết luận dựa trên trạng thái từng step và workflow giữ exit code, không tự nhận đã đọc output log.

Bổ sung kiểm tra artifact đã giải nén trong Windows CI: chạy preflight và START BAT thật từ working directory khác, với đường dẫn chứa khoảng trắng, & và !. BAT phải trả đúng mã 2 khi stdin không tương tác, không gửi tin và không tạo runtime; kiểm tra này cần run mới đạt trước khi tuyên bố thành công.

## Kết quả artifact cuối đã xác minh

Source/artifact commit 5fc13e2 (nhánh phát triển mới). Windows CI:
https://github.com/trantrungchinh2409-ux/Twillight_249/actions/runs/40256355890
Job 121358949082 hoàn tất success lúc 08:54:15 ngày 26/10/2026 (giờ Việt Nam). Step chạy toàn suite, run_portable self-test, preflight Python và verifier ZIP/BAT đều success; upload artifact success. Verifier chạy source giải nén trong đường dẫn có khoảng trắng/&/!, từ cwd khác; preflight DPAPI/SQLite đạt và START BAT thật trả đúng mã 2 khi không có terminal tương tác, không tạo runtime hoặc gửi API. Đây là Windows Server 2022 runner, chưa phải Windows 7 thật.

ZIP cuối: downloads/JAT-Design-Win7-Python38.zip, 46 thành phần kể cả manifest.
SHA-256: bbfdb47947ebc24285af0f6ba66d9dcb213d982690aac70bd0641e5ad6906903.
File tải trên GitHub được đọc lại kiểm byte/hash, không chỉ kiểm file tại workspace. Bản ZIP giữ nguyên sau CI; mục báo cáo này bổ sung sau khi CI hoàn tất, không sửa source runtime đã test hoặc thay artifact.

Đã đối chiếu nhánh nguồn failover và stable-ai/stable-auto/stable-live sau push: giữ đúng SHA trước khi làm. Chỉ push nhánh jat-design/win7-python38-launchers-20261026. Không thay đổi Cloudflare, webhook, bí mật hoặc dữ liệu thật.

## Hotfix console Windows 7 sau phản hồi thực tế

Người dùng đã xác nhận SQLite 3.35.5, Python 3.8.10 x64, DPAPI/mutex/TLS/source qua preflight trên Win7 thật. Chọn mục 1 lỗi ở setup_api.py:51 (print banner Unicode trước khi đọc key), log cuối bị cắt, kết quả process 120. 120 phù hợp lỗi flush stdio lúc thoát nhưng log thiếu exception cuối nên chưa kết luận chính xác WinError trên máy đích.

Thêm win7_console.py trong launcher source: chỉ chuyển hiển thị stdout/stderr và prompt input/getpass sang ASCII trên Win7; không chuyển đổi giá trị input/key/nội dung ứng dụng. Wrapper giữ isatty/fileno và bảo vệ no-echo của getpass. Không thay code vault, DPAPI, API, hạn mức hoặc DB; không đổi cấu hình console hệ thống. Windows mới giữ hiển thị Unicode, có JAT_ASCII_CONSOLE=1 cho kiểm thử ép nhánh tương thích.

Tái hiện hồi quy với console mô phỏng từ chối Unicode: banner gốc đúng dòng 51 ném OSError, banner qua adapter đạt. Test xác nhận prompt ASCII nhưng secret/đường dẫn Unicode trả nguyên vẹn, GetPassWarning vẫn chặn fallback hiện key và phục hồi stream/input sau lỗi. Verifier ZIP Windows ép nhánh ASCII cho START BAT. Đây không thay thế chạy lại menu 1 trên Win7 thật; không tuyên bố đã nghiệm thu lỗi người dùng trước khi họ chạy bản sửa.

Hotfix console commit 53b1d61 đã qua Windows CI:
https://github.com/trantrungchinh2409-ux/Twillight_249/actions/runs/40259269460
Job 121367871794: toàn bộ suite hiện có và test console mới, self-test DPAPI/SQLite, source preflight, ZIP/BAT verifier ép ASCII và upload đều success. Suite source có 142 test; Linux subset chạy 99: 98 passed, 1 native Windows skipped. Tái hiện console Unicode bằng mock là bằng chứng hồi quy, không phải test trên Windows 7 thật; vẫn cần người dùng thử lại mục 1 bằng hotfix. Không gọi Gemini/Zalo thật, không yêu cầu nhập lại secret vào chat.

ZIP hotfix SHA-256: 66a3b5f0cc4059decd50942d87cac95732d8657490ee9e07969d6c3ae38302f4. Artifact đã kiểm CRC/manifest/Python3.8 syntax và đọc lại download từ GitHub; không kèm runtime. Không sửa nhánh stable, các module lõi giữ nguyên.

## TLS diagnostic v2 — phản hồi thực tế Win7

Ảnh người dùng: Google HTTPS certificate validation passed HTTP404, Zalo HTTPS failed. Đã phân biệt: Google TLS thành công; lỗi Zalo theo endpoint, chưa xác định CA/proxy/TLS từ thông báo cũ. Không suy đoán chắc chắn token sai, thiếu chứng chỉ hoặc bị công ty chặn.

Thêm https_probe.py với hai origin cố định không credential. Chỉ trả enum và mã số allowlist, không exception message, URL token, CA subject, proxy credential hoặc response body. Xác minh chứng chỉ/hostname giữ bật. run_portable.check_https chuyển sang helper mới cho mục 4; không đổi Transport/polling/Gemini/key vault/state. Các test mô phỏng cert-code20, TLS reason, DNS, timeout, proxy403 và HTTP404; không phải bằng chứng máy Win7 đã được sửa TLS. Phải chạy lại mục 4 tại máy đích để có mã thật.

## Thu hẹp theo yêu cầu: gói chẩn đoán độc lập Zalo TLS

Giữ nguyên code bot Windows11, không sửa polling/sendMessage/Gemini/state. Thêm CHECK_ZALO_TLS_WIN7.bat + check_zalo_tls.py và gói JAT-Zalo-TLS-Check-Win7.zip riêng, không import jat_design hoặc đọc runtime/DPAPI/DB. Kiểm read-only DNS với thời hạn chờ, proxy tĩnh/PAC và CA override chỉ báo sự hiện diện, HTTPS có hostname/CA verification mặc định; không thử bỏ proxy, đổi resolver hoặc sửa bảo mật.

Kết quả PASS/FAIL và enum/mã cert/TLS/proxy/network; không in địa chỉ IP/PAC/proxy credential/URL chứa token. Explicit proxy CONNECT 403/407 chứng minh từ chối ở proxy; lỗi certificate chỉ chứng minh validation failure, còn timeout/reset/DNS không đủ quy lỗi mạng công ty. 404 Google root vẫn TLS PASS. Kết quả source/mocks không chứng minh mạng Win7 công ty đã hoạt động; cần chạy gói độc lập tại máy đích, không cần token thật.

Gói độc lập commit 5a94ff1 đã qua Windows Python3.8.10 x64 CI:
https://github.com/trantrungchinh2409-ux/Twillight_249/actions/runs/40260916802
Job 121372907097: toàn suite (gồm test phân loại TLS mới), standalone --help, đóng gói độc lập, preflight/ZIP verifier và upload success. Linux subset 109 test: 108 passed, 1 Windows-native skipped. Đây là kiểm chứng chương trình, không phải kết nối thực tế từ mạng công ty Win7. Link ZIP GitHub đã GET200 và đối chiếu SHA-256 af17aad4eaa34f473c994a8378fa1c12a1b647fb7a3bf8125c8dd813b7c39697. ZIP độc lập chỉ có 4 file cần thiết và manifest, không chứa module bot, runtime hoặc secret. Chờ kết quả phân loại trên Win7 trước khi đề xuất sửa CA/proxy/TLS; không tiếp tục sửa code nhận/gửi đã hoạt động.
