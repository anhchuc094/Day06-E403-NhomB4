# ZaloPay AI Spending Classifier Prototype

Prototype mobile web mô phỏng giao diện ZaloPay và một AI agent phân loại chi tiêu.

## Cấu hình OpenRouter

Tạo file `codebase/.env` từ `.env.example`:

```env
OPENROUTER_API_KEY=your_new_openrouter_api_key
OPENROUTER_MODEL=openai/gpt-4o-mini
PORT=8000
```

API key chỉ được đọc bởi Python server và không được gửi xuống browser. OpenRouter là luồng phân loại duy nhất của prototype. Nếu API lỗi hoặc chưa cấu hình, giao diện báo lỗi và cho phép người dùng thử lại; hệ thống không hiển thị kết quả mock thay cho AI.
Server đọc lại `.env` ở mỗi lần phân loại, nên có thể thêm hoặc đổi API key mà không cần khởi động lại.

Không dùng lại `API_KEY`/`LLM_ENDPOINT` của Day04 vì đó là cấu hình cho provider khác, không phải OpenRouter.

## Chạy prototype

Từ thư mục project, chạy:

```powershell
python codebase/server.py
```

Mở `http://localhost:8000`, sau đó bấm **Phân loại bằng AI**.

## Luồng demo

1. OpenRouter AI đọc và phân loại 30 giao dịch.
2. Dashboard hiển thị tổng chi, top category, confidence và insight.
3. Chọn bộ lọc **Cần xác nhận** để xem giao dịch mơ hồ.
4. Hỏi chatbot để tìm giao dịch mơ hồ, khoản chi lớn hoặc giao dịch học phí.
5. Chatbot đề xuất sửa category giao dịch VINUNI từ `Mua sắm` sang `Giáo dục`.
6. Người dùng bấm **Áp dụng** để xác nhận; các số liệu dashboard tự cập nhật.

## Cấu trúc

- `server.py`: backend gọi OpenRouter qua API tương thích OpenAI.
- `spending-agent.js`: agent phía frontend gọi OpenRouter cho classification và chatbot.
- `app.js`: logic giao diện, chatbot, correction path và dashboard.
- `prompts/chatbot-system-prompt.md`: prompt khuôn mẫu điều khiển hành vi chatbot.
- `data/`: giao dịch, kết quả phân loại mẫu dùng làm test fixture và correction mẫu.
- `index.html`, `styles.css`: prototype mobile web.

## Ghi chú

OpenRouter API là bắt buộc để chạy luồng phân loại. File `data/mock-classifications.json` chỉ là test fixture/evidence, không được tải hoặc dùng làm fallback khi chạy prototype.

Chatbot gọi endpoint `/api/chat`. AI chỉ tìm kiếm và **đề xuất** correction; category chỉ thay đổi sau khi người dùng bấm **Áp dụng**.

Có thể chỉnh hành vi chatbot tại `prompts/chatbot-system-prompt.md`. Giữ nguyên placeholder `{{CATEGORIES}}` để backend tự chèn danh sách category hợp lệ. Sau khi sửa prompt hoặc `server.py`, cần khởi động lại Python server.

---

# Codebase

Đây là nơi nhóm nộp toàn bộ phần code của prototype. Mục tiêu là để giảng viên và các nhóm khác nhìn được sản phẩm chạy như thế nào, và mỗi thành viên đã đóng góp ra sao.

## Nhóm cần làm

- Đưa mã nguồn của prototype vào folder này. Nếu prototype được deploy hoặc host ở nơi khác, hãy để lại đường link kèm hướng dẫn truy cập.
- Trong file `README.md` của nhóm, ghi rõ ba điều: cách chạy prototype (các bước cài đặt và biến môi trường nếu cần), những công cụ và API đã dùng (model AI, framework, công cụ dựng giao diện…), và phần phân công ai làm gì.
- Mỗi thành viên nên có ít nhất một commit thực chất trong repo — đây là căn cứ để ghi nhận đóng góp của từng người.

## Lưu ý

Đừng commit những thông tin nhạy cảm như API key hay file `.env`. Nếu prototype cần các biến môi trường, hãy dùng một file `.env.example` để mô tả các biến đó thay vì để lộ giá trị thật.
