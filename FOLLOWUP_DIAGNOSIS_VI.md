# Chẩn đoán FOLLOWUP thực tế — 27/10/2026

## Kết luận có bằng chứng hiện tại

Người dùng báo Win7 Agent đã hoạt động: @bot có trả lời, tên AI JAT/Gemini/typing API hoạt động; FOLLOWUP bật thành công. STATUS có bot/agent/catchall=true, sessions=2, observed.received=4, plain=0, plain_active_member=0. Đây là dữ liệu người dùng cung cấp, không phải kết quả live tại môi trường phát triển.

**Chưa thể kết luận chỉ từ observed.plain=0 rằng Zalo không giao tin.** `reply_verified=false` không tự chặn FOLLOWUP theo sender khi catchall=true; không đổi cờ này để ép PASS. Bộ đếm nằm sau Transport, shared valid_event, kiểm snapshot mode và worker prefilter. Dữ liệu không khớp schema, nhóm/sender/is_bot/text hoặc bị hủy do mode đổi có thể chưa từng tăng bộ đếm. Plain còn có nghĩa kỹ thuật là text KHÔNG chứa đúng chuỗi @Bot JAT Design, không phải đã xác minh người dùng không thao tác @/Reply trên UI.

### Tài liệu chính thức đọc lại HTTP200

- [Hướng dẫn nhóm](https://docs.zaloplatforms.com/docs/BOT/best-practices/build-bot-interaction-with-group): có lưu ý giai đoạn thử nghiệm nội bộ. Bước3 mô tả:
  - “Bot sẽ nhận được sự kiện khi có người dùng ‘Trả lời’ (Quote) một tin nhắn mà Bot đã gửi trước đó.”
  - “Bot sẽ nhận được sự kiện khi người dùng gõ @ và chọn tên của Bot trong tin nhắn.”
- [getUpdates](https://docs.zaloplatforms.com/docs/BOT/apis/getUpdates): polling và webhook loại trừ nhau. Không tài liệu nào ở đây cam kết getUpdates nhận mọi tin thường không @ trong nhóm.
- [Schema webhook/message](https://docs.zaloplatforms.com/docs/BOT/webhook): có GROUP beta và from/chat/text/message_id/date; chưa thấy field đủ chứng minh discriminator Reply-to-bot trong mẫu đã kiểm. Không đoán tên field để bật parser.

**Tin thường không @:** Bot API hiện không có cam kết được tài liệu bảo đảm giao toàn bộ dạng tin này. Công tắc FOLLOWUP trong ứng dụng chỉ xử lý event được API giao; không thể làm Zalo giao thêm tin. Chưa được tuyên bố tính năng này hoạt động live.

**Reply vào bot không @:** được hướng dẫn nhóm mô tả là có sự kiện, vì vậy không được gộp với tin thường rồi kết luận API cấm Reply. Cần xem result trước bộ lọc trên chính bot/nhóm này. Việc giao event và việc có metadata xác minh Reply là hai vấn đề khác nhau.

## Lỗi code đã tái hiện trước khi vá

Main poll chụp snapshot điều khiển **trước** getUpdates. Khi quản lý bật FOLLOWUP lúc request đang chờ, epoch thay đổi. Event mới trả về ngay sau COMMAND=OK vẫn bị loại bởi `controls.valid(snapshot_cũ)`, trước khi tới Worker/counter.

Test tái hiện: bắt đầu poll ở epoch cũ, bật FOLLOWUP ở1001s, trả event mới ở1001.5s; code cũ không gọi Worker dù event mới hơn lệnh bật. Đây là lỗi được xác nhận trong source, **chưa đủ bằng chứng rằng nó là nguyên nhân duy nhất của lần Zalo thật đã báo**.

Bản vá chỉ đổi dispatch sau poll: lấy mode hiện tại, chỉ nhận event có timestamp hợp lệ sau armed của mode đó, rồi xếp job bằng epoch hiện tại. Job cũ đã queued vẫn bị hủy khi OFF/đổi mode; event trước OFF→ON không được hồi sinh. Không nới GROUP/sender/parser, không đổi Gemini/typing/TLS/vault/hạn mức.

## Cài bản chẩn đoán

Gói vẫn là add-on trên mốc Win7 đã chạy tốt; không có file core cũ, runtime hoặc DB/vault. Đóng Agent, chép nội dung JAT-Agent-Addon vào cùng thư mục hiện tại. File Agent app được cập nhật cho lỗi dispatch đã có test; bản Win7 cơ bản và các nhánh stable không đổi. Giữ ZIP Agent trước nếu cần quay lại phiên Agent trước vá.

Chạy CHECK_AGENT_WIN7.bat và SELF_TEST_AGENT_WIN7.bat. Có thể chạy bản Agent vá như cũ; **không cần mở Agent để dùng probe**. Để xác định đường nhận mà không gửi tin bởi bot, ưu tiên probe bên dưới.

## Probe A/B/C — một poller, chỉ đọc, không gửi

1. Gõ QUIT và đợi Agent đóng hẳn. Đóng các poller khác cùng token, không chạy bot ở máy khác đồng thời.
2. Mở **PROBE_FOLLOWUP_WIN7.bat**. Nhập token hiện có bằng nhập ẩn tại máy. Công cụ không đổi token/webhook và không đọc Gemini API vault. Nó dùng getMe/getWebhookInfo/getUpdates qua ReadOnlyTransport; nếu webhook bật sẽ dừng.
3. PhaA: Enter để READY A. **Cùng tài khoản dùng để thử FOLLOWUP**, gửi @bot kèm đúng mã A mới hiện trong đúng nhóm đã duyệt. Phải có RAW_MATCH_RECEIVED mới sang B; sender A chỉ giữ trong RAM để so sánh, không ghi ID hoặc hash.
4. PhaB: Enter để READY B. Cùng tài khoản A, gửi **mã B như tin thường**, không @, không Reply. Mỗi pha khoảng65–105 giây do long-poll. Nếu không có event, chờ kết quả, không gửi hàng loạt.
5. PhaC: Enter để READY C. Cùng tài khoản A, dùng chức năng Reply/Quote của Zalo vào **một tin thật mà bot đã gửi trước đó**, nội dung là mã C, không @. Probe không gửi tin mới để tạo đích Reply.
6. Chỉ gửi sau READY của đúng pha. Một tin @ để đối chứng đường nhận, sau đó chỉ1 tin thường và1 tin Reply; không gửi hàng loạt. Mã mỗi pha khác nhau để event B đến chậm không bị nhầm thành C. Có thể Q giữa các pha hoặc Ctrl+C.
7. Lấy **riêng runtime/agent_followup_probe.json** hoặc ảnh PROBE_META/PROBE_PHASE. Không gửi cả runtime, token, ID hoặc nội dung hội thoại.

Probe chỉ ghi số poll rỗng/nonempty, enum đã biết, shape/boolean, shared_valid_event và dry-run prefilter. Không text, tên người, sender/group/message ID, ID hash, timestamp thô, token hay mã phiên đầy đủ. UNKNOWN enum không được echo giá trị. Tối đa8 metadata gần nhất/pha, tối đa40 nonempty/pha; báo cáo ghi đè đúng file riêng. Không sửa one_shot.db, agent_state.db, ai_reply.db hoặc vault.

Label A/B/C là nhãn do người thử thực hiện, không chứng minh Reply entity. `known_reply_key_present`/`reply_key_shapes` chỉ ghi có hay không và kiểu dữ liệu của4 key quan sát cố định (reply_to_message/reply_to/quote/quoted_message); không đọc/lưu giá trị hoặc xác nhận target. Có key không đồng nghĩa đã xác minh Reply-to-bot; không thấy các key này cũng không chứng minh mọi schema Zalo không có Reply metadata. `dry_worker_would_queue` chỉ mô phỏng BOT/AGENT/FOLLOWUP ON với snapshot phiên còn hạn đọc từ SQLite readonly khi mở probe; không chạy worker hoặc gọi sendMessage. Probe không gia hạn phiên nên session có thể đã hết hạn sau khi Agent đóng — dry queue=false trong trường hợp đó không chứng minh lỗi ở phiên thử trước.

Exit0 nghĩa đã thu xong báo cáo, **không phải FOLLOWUP PASS**. API lỗi được ghi kind/code an toàn; không tự đổi webhook/token hoặc retry gửi.

## Đọc kết quả để phân biệt nguyên nhân

| Kết quả | Kết luận được phép |
| --- | --- |
| A nhận được; B nonempty=0, chỉ empty | Không thấy API giao result cho pha B trong cửa sổ đo. Phù hợp giới hạn tài liệu về tin thường, chưa chứng minh mọi bot/mọi lúc đều như vậy |
| C RAW_MATCH_RECEIVED | API đã giao result khớp mã Reply do người dùng thử; xem các gate tiếp theo, không đổ lỗi API không giao |
| nonempty>0 nhưng shared_valid_event=false | Có result trước helper, nhưng hợp đồng/schema hiện tại bị helper từ chối. Chưa sửa parser khi chưa xác định field/kiểu cần sửa |
| shared_valid_event=true, worker_prefilter_pass=false | Event bị điều kiện nhóm/sender/non-bot/text của Worker loại. Xem flags; không đoán ID hoặc bỏ guard |
| known_reply_key_present=true | Result có ít nhất1 key Reply/Quote trong4 key quan sát; chỉ ghi type, không suy Reply target hoặc bật parser |
| trigger_in_text=true ở pha B/C | Payload được rule hiện tại coi là có chuỗi kích hoạt; observed.plain có thể vẫn0. Không suy ngược từ UI thao tác sang text API |
| worker_prefilter_pass=true nhưng dry queue=false | Có thể không còn session theo ID, hoặc gate queue; probe không tạo/gia hạn session |
| shared/worker gates đều đạt, event mới sau lệnh đổi mode | Bản cũ có lỗi snapshot đã tái hiện; bản vá dispatch xử lý sự kiện mới. Cần thử lại thực tế để xác nhận |
| B/C nonempty>0 nhưng phase_marker_present=false | Có event khác/trễ; không được dùng nó để tuyên bố đúng tin thử đã được giao |
| API_ERROR | Kết nối/API lỗi; không đồng nghĩa poll rỗng. Dừng ở kind/code, không reset token |

Nếu C không được giao dù A được giao và đúng thao tác Reply, hiện chưa đủ bằng chứng để chọn nguyên nhân phía Zalo/cấu hình beta/độ trễ. Giữ báo cáo tối thiểu để đối chiếu tài liệu/hỗ trợ nền tảng, không tự mở webhook hoặc sửa gửi tin.

## Trạng thái nghiệm thu

Bản vá logic snapshot và probe đã được test offline bằng event giả; không dùng mock để tuyên bố FOLLOWUP live thành công. Kết quả kiểm thử cụ thể ở AGENT_NATIVE_TEST_REPORT.json/VALIDATION_AGENT_WIN7.md. Không gửi tin thật hoặc dùng key/token của người dùng tại môi trường phát triển.


## Kiểm thử bản bàn giao

- Toàn suite trên Windows Server2022, **CPython3.8.10 x64:265 test,264 PASS,1 SKIP,0 lỗi**, socket bị chặn, không có key/token ứng dụng.
- Skip là test full CA root+intermediate môi trường riêng; TLS G3 runtime không đổi và đã có test riêng.
- Trước/sau lỗi snapshot, OFF/ON không hồi sinh event cũ, raw empty vs helper/worker reject, Reply key chỉ ghi type, không ghi private data, SQLite đọc readonly và không start worker/gửi trong probe đều có test.
- Một fixture SQLite của test mới giữ connection khi dọn thư mục tạm trên Windows; đã đóng đúng connection và native suite chạy lại PASS. Hàm readonly production vốn đã đóng DB trong finally, không sửa DB logic để né lỗi test.
- Người dùng đã xác nhận Agent trước bản này chạy Win7/tên/Gemini/typing API; **probe và bản vá mới chưa có kết quả Zalo thật**. Không dùng test để khẳng định API đã giao B/C hoặc Reply metadata đã được xác minh.
