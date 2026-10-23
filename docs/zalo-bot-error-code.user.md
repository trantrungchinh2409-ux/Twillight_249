# Bảng mã lỗi - Zalo Bot Platform

> **Nguồn:** https://bot.zaloplatforms.com/docs/error-code/
> **Cập nhật lần cuối:** 06/08/2025
> **Tổng hợp thành Markdown:** 23/10/2026

## Tổng quan

Tài liệu này mô tả các mã lỗi có thể phát sinh khi sử dụng các APIs của hệ thống Zalo Bot Platform. Với các trường hợp lỗi, vui lòng tham khảo thêm thông tin trong trường `description` trong dữ liệu nhận được để biết chi tiết.

Tất cả lỗi trả về đều có dạng:

```json
{
  "error": -1,
  "description": "Chi tiết lỗi cụ thể..."
}
```

## Bảng mã lỗi

| Mã lỗi | Ý nghĩa | Mô tả chi tiết |
| :--- | :--- | :--- |
| **400** | Bad Request | Sai đường dẫn hoặc API Name không hợp lệ. Kiểm tra lại endpoint, method, và tên API. |
| **401** | Unauthorized | Token đã hết hạn hoặc không hợp lệ. Cần làm mới `access_token` hoặc `refresh_token`. |
| **403** | Internal Server Error | Lỗi phía server Zalo (mặc dù mã HTTP là 403). Thử lại sau hoặc liên hệ hỗ trợ nếu lặp lại. |
| **404** | Not Found | Yêu cầu truy cập không hợp lệ. Endpoint không tồn tại hoặc tài nguyên (user_id, message_id) không tìm thấy. |
| **408** | Request Timeout | Quá thời gian xử lý cho phép. Server không phản hồi kịp, nên retry với backoff. |
| **429** | Quota Exceeded | Vượt quá giới hạn sử dụng API cho phép. Đã chạm rate limit / quota của OA. |

## Hướng dẫn xử lý chi tiết

### 400 - Bad Request
- **Nguyên nhân thường gặp:** Sai chính tả API name, thiếu tham số bắt buộc, sai định dạng JSON.
- **Cách xử lý:**
  - Kiểm tra docs của API đang gọi
  - Validate payload trước khi gửi
  - Log lại `description` để biết field nào sai

### 401 - Unauthorized
- **Nguyên nhân:** `access_token` hết hạn (thường sau 24h), token bị thu hồi, sai OA ID.
- **Cách xử lý:**
  ```javascript
  // Refresh token flow
  if (error_code === 401) {
    const newToken = await refreshAccessToken(refresh_token);
    // retry request
  }
  ```
- Lưu ý: Luôn lưu `refresh_token` an toàn.

### 403 - Internal Server Error
- Đây là lỗi 5xx nhưng Zalo trả về mã 403 trong tài liệu bot.
- **Cách xử lý:** Retry sau 1-3 giây, nếu vẫn lỗi 3 lần liên tiếp thì báo cho Zalo Developer Support.

### 404 - Not Found
- Sai URL: ví dụ `/v3.0/oa/message` gõ nhầm thành `/v3.0/oa/messages`
- User không tồn tại hoặc đã block OA
- **Cách xử lý:** Kiểm tra `user_id` và endpoint trên https://bot.zaloplatforms.com/docs/

### 408 - Request Timeout
- Zalo server xử lý quá lâu, hoặc network chập chờn.
- **Cách xử lý:** Implement retry với exponential backoff:
  ```
  retry_delay = 1s, 2s, 4s
  ```

### 429 - Quota Exceeded
- Vượt quá quota: số lượng tin nhắn / số request / giây.
- **Cách xử lý:**
  - Kiểm tra quota trong dashboard OA
  - Implement rate limiter phía client (ví dụ 10 req/s)
  - Dùng queue để dàn trải request
  - Nếu là OA thường, cân nhắc nâng cấp hoặc liên hệ Zalo để tăng quota

## Best Practices chung

1.  **Luôn đọc trường `description`:** Mã lỗi chỉ là nhóm, chi tiết nằm ở `description`.
2.  **Logging:** Log đủ `error_code`, `description`, `request_id`, `timestamp`.
3.  **Retry có kiểm soát:** Chỉ retry với 403, 408, 429. Không retry với 400, 401 (trừ khi đã refresh token), 404.
4.  **Token management:** Tự động refresh trước khi hết hạn 5 phút.
5.  **Rate limiting:** Dùng token bucket để tránh 429.

## Tham khảo thêm

- Docs chính thức: https://bot.zaloplatforms.com/docs/
- Zalo OA API: https://developers.zalo.me/docs/api/open-api-1
- Hỗ trợ: https://account.zalo.me/

---
*File được tổng hợp tự động từ trang docs chính thức của Zalo Bot Platform.*
