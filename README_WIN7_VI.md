# JAT Design — ứng viên portable Windows 7 SP1 x64

**Chưa được xác minh trên máy Windows 7 thật.** Đã build bằng CPython 3.8.10 x64 / PyInstaller 5.13.2 trên Windows 11; bản này dành cho nghiệm thu Win7, không khẳng định tương thích đã hoàn tất. Tài liệu PyInstaller 5.13.2 ghi môi trường chính thức từ Windows 8; vì vậy việc nhắm Win7 bằng toolchain cũ vẫn là ứng viên phải nghiệm thu, không phải cam kết hỗ trợ. Không cần cài Python trên máy đích. Giữ nguyên cả thư mục onedir, không lấy riêng EXE.

## Trước khi chuyển máy

1. Trên Windows 11, đóng mọi bot; không chỉ khóa màn hình. Giữ bản đang chạy tốt để khôi phục. Không chạy bot đồng thời ở hai máy. Khóa mutex chỉ ngăn tiến trình trong cùng phiên đăng nhập Windows, không khóa xuyên máy.
2. Giải nén source nâng cấp, mở EXPORT_PROFILE_WINDOWS.bat; nhập đường dẫn thư mục runtime cũ, không kèm dấu ngoặc kép. Với máy hiện tại là C:\Users\PC\Downloads\JAT-Design-Handoff\work\repository\runtime. Công cụ xuất runtime/transfer-profile-private.zip trong thư mục source nâng cấp.
3. Hồ sơ riêng chỉ chứa nhóm đã xác minh, biên nhận bot, bộ đếm và chống trùng. Không mang Gemini Key, token Zalo, nội dung câu hỏi hoặc file kho DPAPI. Hồ sơ có ID nhóm nên giữ riêng, không gửi GitHub/chat và không đưa vào ZIP phát hành công khai.
4. Chép hồ sơ riêng và thư mục portable sang Win7. Không chép gemini_keys.dpapi hoặc mẫu DPAPI của Win11; khóa và mẫu nhóm phải được mã hóa lại theo tài khoản Windows đích.

## Trên Windows 7

1. Giải nén toàn bộ ZIP vào thư mục có quyền ghi, ví dụ D:\JATDesign; không chạy trong ZIP hoặc Program Files. Máy phải là Windows 7 SP1 x64. Nếu máy thiếu DLL/runtime, dừng và gửi đúng tên lỗi; không tải DLL từ website lạ hoặc tự sửa bảo mật. Bản portable không bundle UCRT/API-set DLL từ Win11. Máy Win7 cần Universal CRT/Visual C++ runtime chính thức phù hợp do quản trị công ty cung cấp; ứng dụng không tự cài hoặc đổi cấu hình hệ thống.
2. Chạy CHECK_PORTABLE.bat: kiểm DPAPI/SQLite/import offline, sau đó HTTPS không dùng credential tới Google và Zalo. Phép kiểm HTTP 400/404 vẫn chứng minh TLS nếu báo certificate validation passed. Chưa chứng minh token/quota hoặc API bot hoạt động. Lỗi chứng chỉ/proxy/mạng công ty phải báo quản trị; không tắt xác minh TLS.
3. Chạy IMPORT_PROFILE.bat, nhập đường dẫn hồ sơ riêng (không có dấu ngoặc kép). Công cụ mã hóa lại mẫu nhóm bằng DPAPI trên máy đích, giữ nguyên bộ đếm/dedup. Không ghi đè dữ liệu đã tồn tại. Nếu xuất hiện profile-import.pending, giữ nguyên thư mục và báo Codex; không tự xóa DB.
4. Chạy SETUP_API.bat. Nhập khóa ẩn, Enter để thêm, Y để xong. Mở lại để A thêm/D xóa/C kiểm đúng một khóa/P chọn chính/Q thoát. C thực hiện một request Gemini thật, có thể dùng quota; không gửi Zalo.
5. Chạy START_WIN7.bat. Nhập Bot Token Zalo ẩn; bot kiểm getMe/webhook/nhóm cũ, mặc định OFF. Chọn ON rồi gửi @Bot JAT Design kèm câu hỏi trong nhóm thử. STATUS xem khóa đang chọn, trạng thái dự phòng, lượt còn và thời gian chờ; OFF tạm ngưng; QUIT rồi đợi thoát để dừng. Không tự xóa webhook.

## Hoạt động và giới hạn

Giữ model/prompt/token/nhóm/cooldown/chống trùng từ bản AI đã chạy. Khóa hỏng riêng được bỏ qua; dự phòng thành công in “Đã chuyển sang API dự phòng #X” (X là số thứ tự trong SETUP_API), không in khóa. Khóa đang chọn được nhớ qua restart. P chọn chính sẽ chọn lại khóa đó. Không chuyển khóa với 429, mạng, lỗi nội dung, Zalo hoặc quyền/billing chung. 429 chờ Retry-After/RetryInfo, không né quota.

10 lượt AI trong 120 giây; lượt lỗi tính bảo thủ. Lượt thứ 10 bắt đầu nghỉ 5 phút, thông báo đúng một lần ở tin khớp tiếp theo sau cooldown; hết nghỉ xử lý tin mới. Không xếp hàng tin cũ. Giữ ON/OFF/STATUS/QUIT, cooldown 10 giây và trạng thái qua restart.

Mất mạng khi đọc getUpdates/getMe: tự chờ 5/10/20/40/60 giây rồi đọc lại; lỗi auth/TLS/giao thức dừng. Lỗi mạng Gemini không xoay khóa, không phát lại câu hỏi cũ, giữ ON chờ tin mới. sendMessage timeout/chưa rõ xác nhận: dừng và giữ khóa chống gửi lặp, tuyệt đối không tự reconnect bằng cách gửi lại. Đã OFF/QUIT trong lúc request đang chạy không thu hồi được request đó.

Khóa màn hình không chủ động dừng tiến trình; sleep/hibernate, đăng xuất, tắt CMD, tắt máy hoặc công ty ngắt mạng có thể làm gián đoạn. Chưa nghiệm thu hành vi khóa màn hình trên Win7. Ứng dụng không sửa power policy, proxy, firewall, chứng chỉ hoặc bảo mật công ty. Cần máy vẫn thức và có mạng.

Log an toàn: runtime/ai_audit.jsonl và bản previous giới hạn dung lượng, managed_ai_status.json; chỉ loại/mã lỗi/trạng thái/số thứ tự khóa, không token/key/câu hỏi/câu trả lời. Giữ runtime để không reset trạng thái. Khi đổi tài khoản Windows/máy phải nhập khóa và nhập hồ sơ lại đúng quy trình.

## Nếu chưa chạy được trên Win7

Bản hiện tại đã build trên Win11 và cần nghiệm thu máy đích. Nếu thiếu import/DLL hoặc TLS không tương thích, dừng tại lỗi thực tế. Phương án build thay thế: máy/VM Windows 7 SP1 x64 được cấp phép, CPython 3.8.10 x64 chính thức, dependency ghim requirements-build.txt, rồi chạy `python scripts/build_win7_candidate.py`. Trên máy build có thể cài Python; máy chạy portable không cần. UCRT và CRT phải do quản trị cung cấp hợp lệ. Không dùng PyInstaller/Python mới hơn tùy tiện để thay thế và không tắt bảo mật.

Chưa triển khai Railway, chưa kích hoạt dịch vụ trả phí. Việc nghiệm thu cuối gồm CHECK_PORTABLE, DPAPI lại sau đóng/mở, một câu Zalo thật, khóa màn hình và rút/cắm mạng; chỉ làm khi Windows 11 đã dừng hoàn toàn.


Nguồn dependency chính thức: [Python cho Windows](https://docs.python.org/3.10/using/windows.html), [PyInstaller 5.13.2 requirements](https://pyinstaller.org/en/v5.13.2/requirements.html), [Microsoft UCRT](https://learn.microsoft.com/en-us/cpp/windows/universal-crt-deployment?view=msvc-160). Win7 SP1 có thể cần bản cập nhật UCRT KB2999226 hoặc bản thay thế phù hợp do quản trị cung cấp, không tự cài từ ứng dụng.

## Chỉ nâng cấp Windows 11 trước

Có thể dùng source nâng cấp trong một thư mục riêng: sau khi dừng bot cũ, EXPORT_PROFILE_WINDOWS.bat đọc runtime cũ, rồi IMPORT_PROFILE_WINDOWS.bat nhập hồ sơ vừa xuất vào runtime mới. Cùng máy và đúng cùng tài khoản Windows 11 thì có thể chép riêng gemini_keys.dpapi từ runtime cũ sang runtime mới để dùng tiếp; không đưa tệp vào ZIP/GitHub, không làm vậy khi chuyển sang Win7. Mở SETUP_API kiểm trạng thái rồi START_AI. Giữ thư mục cũ để khôi phục nhưng không mở đồng thời. Khi quay về máy/bản cũ sau khi đã dùng bot mới, cần chuyển trạng thái mới về đúng quy trình; không dùng DB cũ để reset hạn mức.
