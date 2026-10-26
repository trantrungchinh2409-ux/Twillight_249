# JAT Design — tổng hợp vấn đề Windows 7 và bàn giao kiểm tra tại nhà

Cập nhật: **26/10/2026**. Đây là **một file tổng hợp toàn bộ các sự cố đã được đưa vào cuộc trao đổi về bản Win7, gồm các lỗi người dùng nhắc lại trong buổi làm việc và lỗi phát sinh khi chuẩn bị bản sửa**. Một số log không có timestamp nên không tự gán giờ hoặc khẳng định tất cả đều phát sinh sáng 26/10. Tài liệu ghi bằng chứng đã có, cách xử lý và việc còn cần làm; không yêu cầu viết lại bot.

File này đã gộp nội dung lỗi, quá trình xử lý, link tải, kết quả kiểm thử và hướng dẫn tiếp tục tại nhà; không cần ghép nhiều báo cáo để nắm tình trạng.

## 1. Kết luận hiện tại

**Nguyên nhân TLS đã được khoanh vùng và có cách khắc phục được kiểm chứng trên Win7:** trust mặc định của Python không xác minh được chain Zalo; thêm đúng DigiCert Global Root G3 vào một context riêng thì Zalo TLS PASS.

**Bản tích hợp vào JAT Design đã tạo và kiểm thử offline. Chưa có xác nhận người dùng đã chạy bot thật thành công bằng ZIP tích hợp mới trên Win7.** Vì vậy bước tiếp theo là nghiệm thu bản ZIP ở máy công ty, không quay lại build EXE hoặc sửa logic Zalo/Gemini.

Chạy thành công trên máy nhà Windows11 giúp kiểm tra source/launcher nhưng **không thay thế** kiểm thử Python3.8.10, trust store, DPAPI và mạng công ty trên Windows7.

## 2. Repository và phiên bản cần tiếp tục

- Repository: https://github.com/trantrungchinh2409-ux/Twillight_249
- Source bot gốc: nhánh `jat-design/failover-win7-portable`, commit `61a1a3d9884938736ee83a762e3cdf10cc570105`.
- Nhánh tích hợp TLS hiện tại: **`jat-design/win7-zalo-rootg3-20261026`**.
- Commit tích hợp và ZIP: **`d79845efd54f9ea3d708c9912c85a76d84a2716b`**.
- Các thử nghiệm Cloudflare/webhook trước đây thuộc hướng triển khai cũ, không phải việc cần sửa ở bản Python Win7 hiện tại.
- Không sửa nhánh stable. Không chạy lại vòng lặp GitHub Actions; commit tài liệu/bản bàn giao dùng `[skip ci]`.

### Tải bản hiện tại

[ZIP JAT Design Win7 Python3.8 + G3](https://github.com/trantrungchinh2409-ux/Twillight_249/raw/d79845efd54f9ea3d708c9912c85a76d84a2716b/downloads/JAT-Design-Win7-Python38-G3.zip)

SHA256 của ZIP:

```text
40c59ad3ecc2c1b9d186ebbc0ff4296be5e75323d9a8b8761e4e3b39848a7f6b
```

Link đã được tải lại kiểm tra HTTP200, CRC và hash; chứng chỉ trong ZIP đã được kiểm lại fingerprint. Đây là ZIP source Python, không kèm Python/EXE/DLL, không chứa key/token/database hoặc runtime riêng.

**Không dùng nhầm `JAT-Zalo-DigiCert-Win7.zip` cũ:** bản đó không kèm CA, phải tự tải và đã thất bại ngay tại HTTPS DigiCert trên máy công ty. Bản cần dùng là **`JAT-Design-Win7-Python38-G3.zip`** ở link trên.

## 3. Môi trường đã được người dùng xác nhận

| Thành phần | Máy công ty Windows7 | Máy Windows11 |
| --- | --- | --- |
| Hệ điều hành | Windows7 Professional SP1 x64 | Bản bot cũ đã chạy thành công |
| Python | CPython3.8.10 x64 | Chưa biết phiên bản Python cụ thể |
| SQLite trong Python | 3.35.5, đọc/ghi DB tạm thành công | Không có lỗi được báo |
| DPAPI/mutex/import source | Preflight người dùng báo OK | Bot đã hoạt động; chưa phải nghiệm thu ZIP mới |
| Google/Gemini HTTPS | PASS | Zalo và Gemini đã chạy thành công |
| Zalo HTTPS mặc định | FAIL certificate verify code19 | Đã hoạt động |
| Zalo HTTPS với root G3 riêng | PASS theo phép thử thực tế T2 | Chưa cần thay cấu hình mặc định |

Không nhầm `sqlite3.exe` bên ngoài với module `sqlite3`/`_sqlite3` của đúng Python chạy bot.

## 4. Các lỗi đã gặp và bằng chứng

| Hiện tượng | Điều đã xác định | Hướng xử lý/trạng thái |
| --- | --- | --- |
| EXE cũ lỗi `_sqlite3` | Runtime EXE không dùng được tại máy Win7 | Chuyển sang source với Python3.8.10 đã cài; không build EXE mới, không chép DLL lạ |
| Chọn thiết lập API từng thoát mã120 | Traceback ban đầu bị cắt, không đủ để kết luận riêng từ mã120; đã có bản sửa hiển thị ASCII cho CMD Win7 | Giữ bản launcher/console hiện có; nếu tái diễn, lấy traceback đầy đủ đã che dữ liệu nhạy cảm |
| Google trả HTTP404 | HTTPS đã xác minh được, URL gốc không phải API có quyền | Không coi HTTP404 ở phép kiểm URL gốc là lỗi TLS hoặc lỗi key |
| Zalo TLS code19 | `self_signed_certificate_in_chain`; issuer được người dùng báo là RapidSSL TLS ECC CA G1 | Không đủ để kết luận riêng rằng proxy công ty là nguyên nhân |
| `certutil` báo Missing Issuer | DigiCert Global Root G3 | Phù hợp với việc context có đúng root G3 khắc phục được lỗi |
| Gói chẩn đoán tự tải CA thất bại | HTTPS `https://cacerts.digicert.com/DigiCertGlobalRootG3.crt` cũng fail code19, stage `root_download`, exit1 | Không để Win7 phải tải CA để tự sửa trust; ZIP tích hợp đã đóng sẵn root |

### Kết quả TLS thực tế quyết định cách sửa

Người dùng đã báo các kết quả sau trên Windows7 SP1 x64, Python3.8.10:

| Phép thử | Kết quả |
| --- | --- |
| T1 — Zalo, trust mặc định | FAIL, certificate code19 |
| T2 — Zalo + DigiCert Global Root G3 | **PASS** |
| T3 — Zalo + G3 + intermediate | **PASS** |
| T4 — Google | **PASS** |
| Exit code | **0** |

Vì **T2 đã PASS**, bản tích hợp chỉ cần root G3. Chưa có bằng chứng buộc phải thêm intermediate. Những kết quả này không chứng minh rằng mọi đường mạng/proxy đều như nhau hoặc CRL/OCSP đã được kiểm.

## 5. Bản tích hợp đã làm gì

Hai file `INSTALL_WIN7.bat` và `START_WIN7_PYTHON.bat` đặt biến sau trong `setlocal`:

```bat
set "JAT_ZALO_CA_FILE=%~dp0certs\DigiCertGlobalRootG3.pem"
```

`jat_design/zalo_tls.py` đọc CA riêng, kiểm đúng root pin, identity và thời hạn, tạo SSL context với:

- `ssl.CERT_REQUIRED` và `check_hostname=True`.
- Chỉ root G3 đã pin được nạp vào context Zalo; không cho phép partial-chain.
- File thiếu/hỏng/sai fingerprint hoặc thời hạn/đồng hồ không hợp lệ: dừng an toàn trước khi tạo opener, không fallback bỏ xác minh.

Trong `jat_design/official_api.py`, chỉ thay cách tạo HTTPS opener của `Transport` Zalo. Request, response, API method, timeout, parser và xử lý gửi/nhận giữ nguyên. Redirect vẫn bị từ chối.

**Không thay `SSL_CERT_FILE`, global SSL context hoặc Windows Certificate Store.** Gemini tiếp tục dùng opener/trust mặc định như source cũ. Khi không có `JAT_ZALO_CA_FILE`, đường khởi chạy cũ dùng HTTPS mặc định như trước.

Mục kiểm HTTPS của installer được cập nhật để thử Zalo bằng context mới và Google bằng context mặc định, không cần key/token. Preflight kiểm CA trước khi vào tác vụ bot.

### Chứng chỉ đóng kèm

- File: `certs/DigiCertGlobalRootG3.pem`.
- Subject/issuer: DigiCert Global Root G3.
- Hiệu lực: 01/08/2013–15/01/2038, theo metadata chứng chỉ.
- SHA256 **DER**:

```text
31AD6648F8104138C738F39EA4320133393E3A18CC02296EF97C2AC9EF6731D0
```

**Lưu ý:** fingerprint DER không phải hash của file PEM văn bản. Không so trực tiếp hash file PEM với chuỗi fingerprint DER trên.

Root được lấy từ kho CA tin cậy có sẵn của môi trường thực thi và khớp chính xác pin chính thức do người dùng xác minh; không lấy từ kết nối TLS lỗi và không tuyên bố đã tải mới từ DigiCert. Chữ ký tự ký của root đã được OpenSSL kiểm tra đạt. `certs/PROVENANCE.json` ghi nguồn và phép kiểm. URL tham chiếu chính thức: https://cacerts.digicert.com/DigiCertGlobalRootG3.crt .

## 6. Những phần phải giữ nguyên

Không chỉnh lại các chức năng đã hoạt động trên Windows11:

- Zalo polling, request/response và logic bot.
- Gemini/model/prompt, nhiều API Key và cơ chế failover hiện tại.
- API vault, DPAPI gắn với máy/tài khoản Windows.
- Hạn mức **10 lượt AI/120 giây**, nghỉ **300 giây**, cooldown và trạng thái qua restart.
- Dedup, uncertain-send guard, không tự gửi lại khi chưa biết kết quả gửi.
- Điều kiện nhóm đã duyệt, receipt, webhook/polling và bot mặc định OFF theo luồng cũ.

Các module Gemini, key vault, managed AI, managed limits, state, polling, auto reply, reconnect, portable profile, webhook switch, setup API và SYSTEM_PROMPT được so sánh với bản trước tích hợp và không thay đổi.

Không dùng `verify=False`, không tắt hostname verification, không sửa bảo mật Windows/proxy/firewall, không tự cài CA vào hệ thống, không xóa database để reset giới hạn. Không thêm tính năng mới hoặc rebuild EXE cho bước này.

## 7. Mức kiểm chứng của bản ZIP hiện tại

### Đã kiểm

- 130 test offline được chọn phù hợp môi trường: **127 đạt, 3 bỏ qua vì cần Windows/native CA**.
- Pin/root thật, CA lỗi phải fail-closed, tách context Zalo/Gemini và giữ redirect guard.
- Regression API, Gemini, hạn mức/cooldown, chống trùng, uncertain-send guard, reconnect và console.
- Chữ ký root bằng OpenSSL, fingerprint root, CRC và từng hash manifest trong ZIP.
- Parse Python theo cú pháp3.8; BAT ASCII/CRLF.
- Giải nén vào đường dẫn có dấu cách và `!`, dựng transport offline; xóa CA phải dừng trước khi tạo opener.
- Link ZIP GitHub HTTP200, nội dung tải lại trùng hash đã kiểm.

### Chưa kiểm — không được tuyên bố thay bằng mock

- Chưa chạy bot thật với **ZIP tích hợp mới** trên máy Win7 công ty.
- Test tại môi trường thực thi là Linux, không phải Windows7/CPython3.8.10 thật. Parse cú pháp không thay thế chạy trên đúng interpreter.
- Native DPAPI/vault/profile/failover phụ thuộc Windows chưa chạy lại tại phiên tích hợp; source các phần đó không đổi. Người dùng đã báo DPAPI/SQLite của Python Win7 PASS trước đó.
- Chưa đo lại live TLS từ đường mạng công ty bằng bản tích hợp. Dữ liệu T1–T4 là phép kiểm do người dùng thực hiện trước tích hợp.
- Chưa kiểm CRL/OCSP online. Python TLS mặc định không tự chứng minh revocation PASS. Không bỏ qua cảnh báo chứng chỉ bị thu hồi từ IT.

Chi tiết: [VALIDATION_WIN7_ZALO_TLS.md](VALIDATION_WIN7_ZALO_TLS.md).

## 8. Có thể kiểm tra/sửa gì ở máy nhà?

**Có thể kiểm tra source, CA, cách đóng gói và các test offline tại nhà.** Không cần API key/token để làm các việc này. Không cần CI hoặc build EXE.

1. Mở repository, chọn đúng nhánh tích hợp ở mục2; đọc `README_WIN7_ZALO_TLS_VI.md` và báo cáo kiểm thử.
2. Kiểm ZIP có root, hai BAT và toàn bộ source; đối chiếu SHA256 ZIP ở mục2.
3. Nếu máy nhà có Python3.8.10 x64 đầy đủ, có thể dùng installer để kiểm preflight và mục4 để thử HTTPS không credential. Nếu chỉ có Python mới hơn, launcher từ chối là đúng yêu cầu phiên bản, chưa phải lỗi bot. Không cần đổi Python toàn máy để chỉ xem source.
4. Không cần sao chép key/token/profile riêng từ công ty về nhà để chẩn đoán TLS. DPAPI và cấu hình nhóm thật không phải điều kiện để đọc/test phần TLS riêng.
5. Chỉ sửa khi có lỗi tái hiện và traceback kỹ thuật cụ thể. Nếu máy nhà PASS mà máy công ty FAIL, đối chiếu Python, CA được BAT chọn, đồng hồ và đường mạng; không kết luận bot logic hỏng.

### Test offline cho người hỗ trợ có Python

Tại thư mục source, CMD có thể chạy bộ test tập trung dưới đây; không gọi API và chỉ dùng dữ liệu giả trong test:

```bat
set "PYTHONPATH=tests"
python -m unittest test_zalo_ca_config test_official_api test_https_probe -v
```

Ở phiên tích hợp, nhóm này có 31 test đạt trên Linux. Trên máy nhà phải đọc kết quả thực tế của interpreter được chọn. Không cần chạy toàn suite Windows trên Linux rồi sửa logic chỉ để né các lỗi DPAPI không hỗ trợ.

### Prompt có thể đưa cho phiên hỗ trợ tại nhà

> Tiếp tục repository trantrungchinh2409-ux/Twillight_249, nhánh jat-design/win7-zalo-rootg3-20261026. Đọc TONG_HOP_LOI_WIN7_JAT_DESIGN.md, README_WIN7_ZALO_TLS_VI.md và VALIDATION_WIN7_ZALO_TLS.md trước. Win7 Python3.8.10/SQLite/DPAPI đã kiểm được; Zalo TLS mặc định fail19 nhưng context có DigiCert Global Root G3 đã PASS thật. Bản tích hợp tại d79845e chỉ gắn root riêng cho transport Zalo, đã có ZIP đóng CA. Hãy kiểm tra bản hiện tại, không viết lại bot, không build EXE, không sửa Gemini/vault/limits/dedup/failover hoặc stable, không chạy vòng lặp CI, không yêu cầu key/token để chẩn đoán. Chỉ sửa tối thiểu khi có bằng chứng lỗi cụ thể; giữ SSL và hostname verification.

## 9. Nghiệm thu tiếp trên máy Win7 công ty

1. Đóng mọi bot cũ. Nếu cập nhật trong cùng thư mục/cùng tài khoản Windows, giữ nguyên `runtime/`; ZIP không chứa runtime nên không xóa hoặc thay DB/kho riêng.
2. Giải nén toàn bộ ZIP tích hợp. Kiểm thấy `certs/DigiCertGlobalRootG3.pem`. Không chỉ chép riêng BAT, không chạy từ trong ZIP.
3. Chạy `INSTALL_WIN7.bat`: cần preflight Python/SQLite/DPAPI và dòng `OK: Zalo-only root G3... No CA download.` Nếu fail, giữ mã lỗi và dừng.
4. Chọn mục4 kiểm HTTPS. Mong đợi Zalo và Google đều báo certificate validation passed. HTTP404 tại URL gốc có thể chấp nhận cho phép đo TLS; không chứng minh bot có quyền API.
5. Sau khi HTTPS đạt, thiết lập Gemini key theo menu1 bằng nhập ẩn, Q kết thúc; chạy `START_WIN7_PYTHON.bat`, nhập token Zalo tại máy theo luồng cũ. Các cổng nhóm/webhook vẫn phải đạt trước khi bật ON.
6. Nếu đổi máy/tài khoản hoặc thư mục, dùng luồng xuất/nhập hồ sơ đã có. Không chép kho DPAPI sang tài khoản khác, không xóa DB và không chạy hai bản bot song song.
7. Nếu gặp lỗi, chỉ gửi tên BAT, bước lỗi, mã kỹ thuật và ảnh đã che thông tin riêng. Không gửi token/key, nội dung tin nhắn, ID nhóm/người dùng hoặc thư mục runtime.

## 10. Nếu còn lỗi, cần bằng chứng nào?

| Lỗi còn gặp | Kiểm tiếp tối thiểu |
| --- | --- |
| Không tìm Python / exit20 | Đúng Python3.8.10 x64, đường dẫn python.exe được installer chọn |
| SQLite / exit21 | Module của đúng interpreter, không lấy SQLite/DLL từ EXE cũ |
| Preflight exit22 | File root còn đủ, đúng pin và đồng hồ; DPAPI/TLS/import. Mã này là nhóm lỗi, chưa đủ phân biệt riêng nguyên nhân |
| Zalo tiếp tục fail19 trong mục4 | Có chạy đúng BAT/bản ZIP mới không; context riêng đã được bật không; đường mạng/chain có thay đổi không. Không tự thêm CA khác |
| Google TLS đổi từ PASS sang FAIL | Đường mạng/đồng hồ/default trust hiện tại; xác minh không có cấu hình SSL toàn tiến trình do thao tác bên ngoài. Code tích hợp không đặt SSL_CERT_FILE |
| TLS PASS nhưng API bị từ chối | Xử lý lỗi API/quyền/webhook theo mã an toàn; đây là lớp khác với chứng chỉ, không bỏ TLS verification |
| Không có hồ sơ nhóm/receipt | Dùng luồng chuyển hồ sơ đã có, không sửa guard để tự chấp nhận nhóm |
| DPAPI không giải mã được sau chuyển máy | Kho gắn máy/tài khoản; nhập lại key tại máy đích và chuyển hồ sơ đúng luồng |

Mục tiêu nghiệm thu cuối: bản source Python3.8 trên Win7 dùng root riêng cho Zalo, Google/Gemini giữ trust cũ, bot chạy theo logic đã thành công trước đây và các giới hạn/guard không thay đổi.


## 11. Danh sách đầy đủ các lỗi và vướng mắc trong buổi làm việc

Mục này bổ sung cả các log lỗi cũ người dùng đưa lại và lỗi của môi trường chuẩn bị gói. Không coi lỗi môi trường Codex/GitHub là lỗi của máy Win7.

| STT | Lỗi / vướng mắc | Bằng chứng hoặc mã | Đã xử lý đến đâu |
| --- | --- | --- | --- |
| 1 | EXE cũ không nạp được SQLite | `_sqlite3` | Dùng Python3.8.10 x64 trực tiếp; người dùng đã xác nhận module SQLite3.35.5 đọc/ghi thành công. Không build lại EXE |
| 2 | Nhầm SQLite cài ngoài với SQLite của Python | Có SQLite chưa đồng nghĩa `_sqlite3` của interpreter chạy được | Preflight kiểm đúng module trong Python. Trường hợp người dùng hiện tại đã PASS |
| 3 | Chọn menu1 API Gemini bị traceback rồi thoát | `win7_python.py:118 -> install_menu:89 -> setup_api.py:51`, kết quả120; dòng exception cuối không có trong log ban đầu | Đã có bản console ASCII. Không khẳng định chính xác exception gốc chỉ từ mã120; cần traceback đầy đủ nếu lặp lại |
| 4 | Chạy bot báo lỗi TLS nhưng thiếu mã sâu | `OFF - loai=tls ma=None`, kết quả1 | `ma=None` chỉ là wrapper không có mã API, không phải kết luận token sai. Công cụ riêng sau đó lấy được verify code19 |
| 5 | Google hiện HTTP404 gây hiểu nhầm lỗi HTTPS | `HTTPS certificate validation passed, HTTP 404` | Đây là TLS PASS ở URL gốc. Không cần sửa API key để xử lý HTTP404 của phép kiểm này |
| 6 | Zalo HTTPS lỗi nhưng thông báo cũ ẩn chi tiết | `Zalo: HTTPS failed; details hidden, no security settings changed` | Bổ sung diagnostic chỉ đọc với category/code an toàn; không gọi API có credential |
| 7 | Zalo không xác minh được chain | DNS PASS, TLS FAIL; `category=CERTIFICATE`, `cause=self_signed_certificate_in_chain`, `certificate_code=19`, exit1 | Root-only T2 thực tế đã PASS; bản tích hợp đưa root G3 vào context Zalo riêng |
| 8 | Thiếu issuer/root trong đường xây chain | Issuer RapidSSL TLS ECC CA G1; certutil `Missing Issuer: DigiCert Global Root G3` | Root G3 đã xác minh pin. T3 cũng PASS nhưng T2 đủ, nên không bổ sung intermediate vào ZIP runtime |
| 9 | Nghi ngờ proxy công ty / thiếu root / revocation | Mã19 có thể có nhiều nguyên nhân; các log đầu chưa phân biệt đủ | Kết quả T2 chứng minh root riêng khắc phục được trên đường kết nối đã thử; không có bằng chứng để kết luận proxy là nguyên nhân duy nhất. Chưa đo CRL/OCSP |
| 10 | Môi trường chuẩn bị gói không tải được DigiCert qua HTTPS | Các lần truy cập DigiCert bị giới hạn đường mạng; lần kiểm cuối báo `URLError -> OSError` cho cả root và intermediate | Không bypass SSL/HTTP/mirror, không lặp CI tiếp. Cuối cùng lấy root đã tin cậy có sẵn, DER khớp tuyệt đối pin đã xác minh và kiểm chữ ký bằng OpenSSL |
| 11 | GitHub Actions bước tên “Fetch official HTTPS, pin root, verify public CA signatures” lỗi | Run cuối `40297807016`, job `121488041263`, step4 exit1 | Metadata `stage=tests`: fetch/pin/signature đã exit0, sau đó unit test lỗi. **Không được kết luận lần CI cuối lỗi tại URL tải CA chỉ vì tên step có chữ Fetch** |
| 12 | Không đọc được chi tiết traceback của CI | Endpoint log công khai trả HTTP404, giao diện yêu cầu đăng nhập | Chỉ xác định được stage và exit1, chưa biết test cụ thể. Đã dừng retry; đây là giới hạn truy cập log, không chứng minh code bot lỗi |
| 13 | Gói chẩn đoán không có CA, Win7 phải tự tải | `JAT-Zalo-DigiCert-Win7.zip` bản đầu là downloader | Không đạt mục tiêu offline thực sự. Không dùng lại gói này để chạy bot; thay bằng ZIP runtime G3 ở mục2 |
| 14 | Python Win7 cũng không tin HTTPS của DigiCert | `OFFICIAL_BUNDLE=FAIL`, `stage=root_download`, URL `https://cacerts.digicert.com/DigiCertGlobalRootG3.crt`, category CERTIFICATE, code19, exit1 | Đây là lỗi thật người dùng đã chạy. Phải có CA đóng sẵn, không tiếp tục bắt Win7 tự tải CA qua kết nối đang không xác minh được |
| 15 | Chưa thể đóng gói offline khi chưa có chứng chỉ đã xác minh | Báo FAIL trước đó vì chưa lấy được file CA đủ bằng chứng trong workspace | Tình trạng này đã thay đổi: root khớp pin được tìm thấy trong CA store môi trường, kiểm chữ ký đạt, đã đóng trong ZIP tích hợp. Không còn là “ZIP hiện tại thiếu CA” |
| 16 | Chạy toàn suite Windows trên Linux có lỗi nền tảng | Lần cũ: 167 test, 1 failure, 22 errors, 4 skipped; nhiều lỗi cần Windows DPAPI/encrypted backup | Không tính thành test đạt, không sửa bot để ép Linux hỗ trợ DPAPI. Phiên tích hợp chạy suite phù hợp: 127 đạt/3 skipped; native Windows vẫn cần nghiệm thu |
| 17 | Chưa nghiệm thu bản tích hợp mới trên Win7 | Có T1–T4 PASS/FAIL thực tế cho công cụ TLS, chưa có log bot từ ZIP d79845e | Đây là việc còn lại chính: preflight, menu4 HTTPS, rồi chạy bot theo luồng cũ. Không tuyên bố bot mới đã live thành công |

### Các điểm dễ nhầm cần nói rõ với người sửa tại nhà

- **Mã120 không phải verify code19.** Một mã thuộc tiến trình/menu trước đây, một mã thuộc xác minh chứng chỉ. Không gộp thành một nguyên nhân.
- **HTTP404 Google không phải proxy CONNECT403.** HTTP status của URL gốc sau TLS và lỗi tunnel/proxy là hai lớp khác nhau.
- **CI lỗi không đồng nghĩa Win7 lỗi.** CI có lỗi unit test chưa đọc được chi tiết; máy Win7 có bằng chứng TLS cụ thể. Không cần CI phải xanh mới có thể kiểm tra ZIP đã đóng root tại máy đích.
- **Root fingerprint không phải checksum ZIP hoặc checksum PEM.** Xem đúng hai chuỗi khác nhau ở mục2 và mục5.
- **T2/T3 PASS chưa phải bot live PASS.** Nó chứng minh chain/hostname ở phép đo, không chứng minh quyền token, trạng thái webhook, hồ sơ nhóm hoặc Gemini quota.
- **Không có intermediate trong ZIP mới không phải thiếu CA cần thiết đã chứng minh.** Root G3 có sẵn và root-only đã PASS trên máy người dùng.

## 12. Lỗi lịch sử thuộc Cloudflare — để tránh lẫn với Win7

Cuộc trao đổi còn có các sự cố từ hướng Worker/webhook trước khi chuyển sang Python polling. Không có đủ mốc để gọi những sự cố này là lỗi “sáng nay”; ghi ở đây để người tiếp nhận thấy đầy đủ lịch sử mà không sửa sai hệ thống.

| Hướng cũ | Bằng chứng đã được báo trước đó | Liên quan bản Win7 hiện tại |
| --- | --- | --- |
| Deploy/API qua proxy | Có báo proxy403 CONNECT trong giai đoạn Cloudflare | Không phải bằng chứng mạng Zalo trên Win7 hiện tại vẫn bị chặn |
| Quan sát WebSocket | Wrangler tail WebSocket bị proxy chặn403, hai event cũ không lưu | Không dùng WebSocket để sửa Python polling |
| Phiên thu D1 | Phiên quan sát hết hạn, cần mở lại; có các lần chưa thấy event A/C | Không dùng D1 để sửa trust store của Python Win7 |
| Callback Zalo tới Worker | testWebhook chính thức báo `webhook.http.403`; cần phân biệt Edge/Access/đường Zalo bằng bằng chứng | Không liên quan trực tiếp code19 khi Python Win7 gọi Zalo HTTPS |
| GROUP mention contract trong Worker | Chưa có bằng chứng đầy đủ để mở parser/gửi nhóm ở hướng Cloudflare | Không tự mang thay đổi/parser/guard từ nhánh Cloudflare sang bot Windows11 đã hoạt động |

Không deploy Worker, đổi domain, tắt WAF/Access hoặc chỉnh Cloudflare để giải quyết lỗi HTTPS Win7 đã được root G3 khắc phục.

## 13. Việc còn lại duy nhất trước khi kết luận “đã chạy được Win7”

- Dùng đúng ZIP **Python38-G3** tại mục2, giữ dữ liệu runtime.
- Preflight trên máy công ty đạt, có dòng xác minh Zalo-only root G3.
- Menu4: Zalo và Google đều TLS PASS.
- Chạy bot bằng START_WIN7_PYTHON.bat, các cổng quyền/webhook/nhóm/vault theo luồng cũ đạt.
- Thử bot trong phạm vi đã duyệt, giữ giới hạn và chống trùng; không mở bot trên hai máy cùng lúc.

Nếu đạt các bước này thì ghi log nghiệm thu đã lọc vào phiên hỗ trợ tiếp theo. Nếu chưa đạt, sửa theo mã lỗi tại đúng bước, không làm lại dự án từ đầu.
