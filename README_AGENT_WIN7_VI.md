# JAT Design Agent — gói bổ sung Win7/Python3.8.10

Bản phát triển riêng, kế thừa mốc Win7 đã chạy tốt `53f5976`/tag `jat-design-win7-accepted-20261027`, báo cáo lưu mốc `8dcb83e`. Không sửa bất kỳ file bot cũ nào. Không build EXE, không đổi webhook, không Railway. Gói ZIP là **add-on**, cần chép vào đúng thư mục bản Win7 đang hoạt động; không phải bot mới từ đầu.

## Những gì bản này làm

- Tên riêng theo **bot ID + group ID + sender ID thật**, gán bằng mã xác minh do đúng thành viên gửi và người quản lý xác nhận; không đọc tên ảnh/không ghép ID theo vị trí.
- Mỗi người một phiên 5 phút; tối đa6 cặp hỏi/đáp gần nhất (12 message context). Phiên và tên nằm trong SQLite; nội dung/định danh được mã hóa DPAPI theo tài khoản Windows.
- `AGENT ON/OFF` độc lập với `ON/OFF` của bot. Cả hai mặc định OFF mỗi lần mở; khi AGENT OFF, bot cơ bản vẫn dùng luồng cũ và không thêm bộ nhớ.
- **Hỏi tiếp dựa sender ID**: quản lý có thể bật riêng FOLLOWUP; người đã @bot mở phiên có thể nhắn tiếp không @ nếu API chuyển tin đó tới bot. Người không có phiên bị bỏ qua.
- **Nhận diện Reply trực tiếp** là chức năng khác: chưa có metadata/hợp đồng đủ bằng chứng trong mẫu Zalo hiện có, nên runtime không đoán `reply_to_message`, không tuyên bố đã phân biệt Reply bot/người khác.
- Typing dùng API `sendChatAction` chính thức với `action=typing`. Không gửi tin “đang nhập...” riêng. API hỗ trợ theo tài liệu, hiệu ứng thật còn chờ bạn kiểm Zalo.
- Một poller, một worker Gemini/gửi riêng. Chờ tối thiểu2.5 giây từ lúc nhận event nếu model đã xong; model lâu hơn thì không cộng thêm2.5 giây. Polling không bị chặn bởi model/chờ gửi.
- Cùng `ai_reply.db`, vault và cơ chế giới hạn cũ: không tạo ngân sách riêng cho Agent, không reset bộ đếm khi rollback.

## 1. Cài gói bổ sung — không thay bản cũ

1. Giữ ZIP bản ổn định và **giữ nguyên runtime/** trên máy. Đóng mọi bot/poller trước khi cập nhật.
2. Giải nén ZIP add-on. Mở thư mục **JAT-Agent-Addon** bên trong.
3. **Chép toàn bộ nội dung trong JAT-Agent-Addon** (các BAT, run_agent_win7.py, thư mục jat_design/tests/scripts và tài liệu) vào **cùng thư mục đang có START_WIN7_PYTHON.bat, CHECK_WIN7.bat và runtime**. Không chép thành `.../JAT-Agent-Addon/runtime`, không nhân bản runtime ra thư mục thử mới.
4. Add-on chỉ có file mới. Không thay SYSTEM_PROMPT.txt, START_WIN7_PYTHON.bat, getUpdates/sendMessage, Gemini, TLS G3, DPAPI hoặc file core cũ.
5. Chạy **CHECK_AGENT_WIN7.bat**. Nó kiểm hash mốc source, môi trường và hồ sơ/vault offline, không gọi Zalo/Gemini.
6. Chạy **SELF_TEST_AGENT_WIN7.bat**. Test chỉ dùng dữ liệu giả trong thư mục tạm, không gửi tin/không dùng key thật. Trên Windows còn có test DPAPI native của Agent.

Nếu báo `E60 AGENT_BASE_MISMATCH`, thường là chạy add-on trong thư mục riêng hoặc file base khác mốc đã xác nhận. Dừng, không xóa runtime và không tự sửa hash để ép chạy. Base phải là bản Win7 LocalGroup đã hoạt động; [ZIP base đã xác nhận](https://github.com/trantrungchinh2409-ux/Twillight_249/raw/53f59763c93ad05dcc2d914c38478083e657ddf6/downloads/JAT-Design-Win7-Python38-LocalGroup-20261027.zip) vẫn được giữ nguyên.

## 2. Gán 7 tên theo tài khoản thật

Chạy **SETUP_AGENT_NAMES_WIN7.bat** khi bot khác đã đóng. Nhập token Zalo ẩn trong CMD, không gửi token lên chat/GitHub. Công cụ kiểm getMe, webhook OFF và đối chiếu nhóm đã được duyệt trong hồ sơ hiện có.

| Nhãn để quản lý chọn | Tên bot sẽ dùng |
| --- | --- |
| Hoàng Giáp | LÊ KHẢI GIÁP |
| Bạn (phó nhóm) | AI JAT |
| Bot JAT Design | BOT JAT DESIGN |
| Bùi Quang Khải(C lò xo) | KHẢI LÒ XO |
| Đăng | ĐĂNG Đ |
| Đức Mười | NGUYỄN VĂN MƯỜI |
| Trịnh Quang Thành | THÀNH BỐC PHÉC |

Số1–7 **chỉ chọn tên cần gán**, không phải thứ tự tài khoản/ID trong nhóm.

Với mỗi thành viên:

1. Chọn tên muốn gán. Người quản lý xác định đúng người cần liên kết; nếu API không cho tên thì yêu cầu chính người đó xác nhận tên họ muốn được gọi.
2. Chỉ khi hiện **READY NAME**, yêu cầu **đúng người đó** gửi @bot kèm mã JAT-NAME mới trong đúng nhóm đã duyệt.
3. Công cụ lấy sender_id từ event thật, không in ID hoặc text.
4. Người quản lý chỉ gõ **XAC NHAN** khi đã xác minh đúng người. Đây cũng là xác nhận đổi tên cũ của chính tài khoản vừa nhận.
5. Tên đã thuộc tài khoản khác sẽ bị từ chối. Muốn thay liên kết, dùng `X` và `GO TEN` để gỡ đúng tên rồi xác minh lại; không âm thầm chuyển tên sang ID khác.
6. Chọn3 cho bot: dùng bot ID thật từ getMe, không chờ một thành viên giả làm bot.

Có chọn0 để nhập tên khác tối đa64 ký tự. Tên chưa được gán sẽ gọi chung “bạn”, không tự suy tên hiển thị. Định danh và tên lưu DPAPI trong `runtime/agent_state.db`, tồn tại qua restart. Gán tên là công cụ chỉ đọc API: không gửi tin hoặc đổi webhook.

## 3. Chạy Agent và mở phiên

Đóng tool gán tên, chạy **START_AGENT_WIN7.bat**, nhập token ẩn. Startup kiểm hồ sơ thật; không tạo hoặc sửa one_shot.db.

Trong CMD:

```text
ON
AGENT ON
STATUS
```

- `ON`: bật bot; `OFF`: chặn tạo phản hồi mới và hủy đáp án đang chờ.
- `AGENT ON`: bật phiên/bộ nhớ cho các tin gọi bot. Không tự bật bot nếu bot còn OFF.
- `AGENT OFF`: hủy job Agent còn chờ và trở lại bot cơ bản cho các câu mới khi bot vẫn ON.
- `STATUS`: số phiên, số pending, lượt còn lại, thời gian pause/Google wait, API đang chọn, guard và bộ đếm nhận; không có key/token/ID/text.
- `MEMORY CLEAR`: hủy các job cũ và xóa lịch sử/phiên Agent; không xóa tên, DB hạn mức hoặc dedup.
- `QUIT`: dừng; không tự gửi lại.

Thành viên @Bot JAT Design kèm câu hỏi để mở phiên riêng. Câu đã gửi thành công được ghi vào bộ nhớ của đúng ID. Lịch sử không trộn khi nhiều người hỏi xen kẽ. Vẫn dùng chuỗi kích hoạt của bản đã chạy tốt, **không tuyên bố xác minh entity mention thật chỉ nhờ chuỗi tên**.

### Bật hỏi tiếp không @ — lựa chọn riêng của quản lý

Mặc định **FOLLOWUP OFF**, chỉ tin có chuỗi gọi bot được xử lý như trước.

```text
FOLLOWUP ON
```

Lệnh đầu chỉ nhắc xác nhận rủi ro. Nếu quản lý đồng ý, gõ:

```text
FOLLOWUP ON XAC NHAN
```

Sau đó một người đã mở phiên bằng @ có thể hỏi tiếp không @ trong 5 phút tính từ tương tác hợp lệ gần nhất, **nếu Zalo chuyển event đó tới getUpdates**. Phiên của người khác không bị đổi. Người không có phiên vẫn bị bỏ qua. `CATCHALL` là tên lệnh tương đương, cũng phải xác nhận; không bật mặc định.

Tắt lại bất cứ lúc nào:

```text
FOLLOWUP OFF
```

### Giới hạn tránh chen ngang phải hiểu trước khi bật

Khi không có Reply/target metadata đã xác minh, chương trình **không thể chắc chắn biết một câu không @ của người đang có phiên là nói với bot hay với thành viên khác**. FOLLOWUP là lựa chọn nhận theo sender_id trong phiên, không phải nhận diện Reply. Vì vậy mặc định OFF, cần quản lý đồng ý, và nên dùng trong nhóm thử/lúc chủ động trò chuyện với bot.

Nếu người đang có phiên muốn nói chuyện với người khác: kết thúc/tạm dừng phiên trước bằng `@Bot JAT Design /end` hoặc `/pause`; quản lý có thể tắt FOLLOWUP cho toàn nhóm. Không tự đoán người được nói tới từ tên hiển thị hoặc text. Nếu sau này có adapter metadata đã xác minh, bằng chứng đang trả lời người khác sẽ được ưu tiên bỏ qua; hiện runtime chưa có adapter đó.

### Hạn chế đường nhận từ Zalo

Tài liệu nhóm hiện mô tả @bot và reply bot là hai đường bot nhận event. **Chưa kiểm chứng tin thường không @ có được Zalo chuyển tới getUpdates trên bot/nhóm của bạn hay không.** Bật FOLLOWUP chỉ cho phép xử lý những event API thực sự giao, không làm API giao thêm tin.

Sau kiểm thử offline PASS, có thể thử một câu tiếp của chính tài khoản vừa mở phiên. Trong STATUS xem:

- `observed.received`: event text của thành viên trong đúng nhóm đã tới bước nhận.
- `observed.plain`: trong đó không có chuỗi gọi bot.
- `observed.plain_active_member`: plain event thuộc thành viên có phiên theo cache hiện tại.

Nếu @ tới nhưng câu thường không tới, chưa thể khẳng định tính năng live đã hoạt động; cần xác minh giới hạn API, không sửa parser hoặc đổi webhook để ép có tin. Có thể tiếp tục @bot trong cùng phiên để dùng bộ nhớ theo ID. Bộ đếm không lưu text/ID và không chứng nhận Reply metadata.

## 4. Kết thúc và xóa lịch sử

Trong nhóm, dùng `@Bot JAT Design /end`, `/stop`, `/pause`, `/clear` hoặc `/xoa` để đóng/xóa **phiên của chính sender_id đó**. Không gọi Gemini hoặc gửi tin xác nhận riêng. Dùng @ để đảm bảo đường nhận như bản cũ; lệnh không @ chỉ hoạt động khi FOLLOWUP bật và API có giao event.

Hết5 phút không tương tác hợp lệ, phiên không còn dùng được. Lịch sử đã mã hóa bị xóa khỏi bảng khi worker dọn hoặc lần mở ứng dụng tiếp theo; lúc chương trình đóng không có tiến trình nền tự dọn. Tên không bị xóa theo TTL. Store bật SQLite secure_delete cho DB Agent; không đọc/lưu toàn bộ lịch sử nhóm.

## 5. Độ trễ, nhiều người và giới hạn

- Có một worker AI/gửi, polling chạy riêng nên model hoặc delay không chặn getUpdates. Dùng worker nối tiếp để vault/failover và SQLite không bị trộn thread; nhiều phiên thành viên vẫn độc lập.
- Mỗi người tối đa1 request pending; queue tối đa32, job đợi quá60 giây bị bỏ, không phát lại sau restart.
- Khi không vướng gate, gửi khoảng2.5 giây sau nhận nếu Gemini sẵn sàng; Gemini lâu hơn thì gửi khi có kết quả. **Cooldown10 giây cũ và hạn mức vẫn có ưu tiên**, vì vậy nhiều người đồng thời có thể chờ lâu hơn3 giây. Không hứa mọi câu đều2–3 giây khi bị throttle.
- Tối đa10 lượt AI/120 giây cho nhóm/bot hiện tại, nghỉ300 giây như cũ. Dùng cùng bảng trạng thái với bot cơ bản; key lỗi riêng có thể failover, 429 vẫn chờ và không quay key né quota.
- Ngoài cooldown nhóm, Agent giữ gate10 giây theo người và chống pending trùng. Notice nghỉ của engine cũ không phải lời đáp AI mới.
- OFF/AGENT OFF/đổi chế độ sẽ vô hiệu job cũ, kể cả sau OFF rồi ON lại. Kiểm ON/OFF, phiên, slot đã được cấp và provider wait trước gửi.
- HTTP send đã khởi hành không thể thu hồi; timeout/không rõ kết quả giữ auto_block/dedup, không thử gửi lại. Chỉ một trường hợp đã chứng minh chưa gọi HTTP do hủy mới được gỡ marker tạm của chính lần hủy đó.

Typing có endpoint chính thức: https://docs.zaloplatforms.com/docs/BOT/apis/sendChatAction . Một lần best-effort trước model, timeout2 giây, không retry, không gửi placeholder. `typing_api_last=true` trong STATUS nghĩa API đã trả ok cho lần gọi gần nhất, **không thay thế việc bạn nhìn thấy typing thật trên Zalo**. Tại phiên bàn giao chưa có token để thử live.

## 6. Rollback

1. Gõ QUIT và đợi cửa sổ Agent kết thúc. Nếu đang có HTTP, chờ nó kết thúc an toàn.
2. Chạy **ROLLBACK_WIN7.bat** hoặc START_WIN7_PYTHON.bat cũ.
3. Không xóa/đổi tên ai_reply.db, one_shot.db, vault hoặc runtime. Bot cũ dùng đúng cùng counters/dedup/guard, không cấp lại10 lượt mới.

Không chạy bản cũ và Agent đồng thời. Cùng mutex vault/token sẽ chặn xung đột trong phiên Windows; vẫn phải đóng bản ở máy khác. Không cần xóa agent_state.db để rollback; bản cũ bỏ qua DB đó. Muốn dọn hội thoại dùng MEMORY CLEAR trước khi thoát.

## 7. Kế hoạch thử thật sau offline PASS

1. CHECK_AGENT và SELF_TEST_AGENT đạt, gán tên bằng thử nonce chỉ đọc từng người, không gửi hàng loạt.
2. ON, AGENT ON; một người @ hỏi, quan sát đúng tên/typing và thời gian khi không vướng cooldown.
3. Hai người khác hỏi xen kẽ bằng @, kiểm không trộn tên/bối cảnh.
4. Quản lý bật FOLLOWUP có xác nhận; người A hỏi tiếp một câu không @, người B chưa có phiên nhắn thường. Kiểm STATUS xem API có giao event và chỉ A được xử lý.
5. Dùng @/end để người A nói chuyện ngoài phiên; tắt FOLLOWUP nếu không muốn nhận mọi tin của người đang có phiên.
6. OFF khi đang chờ để kiểm hủy. Không cố tạo timeout gửi thật hoặc spam quota; các ca đó đã test offline.

**Đã test offline; chưa nghiệm thu Agent live trên Win7/Zalo.** Chi tiết kết quả và phần cần xác minh trong VALIDATION_AGENT_WIN7.md. Không đưa API key/token/runtime lên GitHub/chat.
