# Batch 02 · Day 06 — AI Product Hackathon


---

## Sản phẩm của nhóm

**Tên sản phẩm:** ZaloPay AI Spending Classifier

Prototype dùng AI để phân loại 30 giao dịch ví điện tử, hiển thị dashboard tổng hợp, đánh dấu giao dịch cần xác nhận và cho phép người dùng sửa category khi AI sai.

### Cách chạy

```powershell
python codebase/server.py
```

Sau đó mở `http://localhost:8000` và bấm **Phân loại bằng AI**.

## Thành viên và phân công commit

> Bổ sung mã học viên chính xác trước khi nộp bài. Mỗi thành viên cần tự kiểm tra, cải thiện và hiểu phần được giao trước khi commit; không chỉ commit lại file do người khác làm.

| Thành viên | Mã học viên | Trách nhiệm chính | File nên phụ trách và commit |
|---|---|---|---|
| Nguyễn Thành Lam | _Bổ sung mã HV_ | Dữ liệu demo, evidence và các case AI sai/không chắc | `codebase/data/transactions.json`, `codebase/data/mock-classifications.json`, `codebase/data/corrections.json`, `codebase/data/README.md` |
| Trần Văn Quang | 2A202600798 | Giao diện frontend, dashboard, danh sách giao dịch và correction UX | `codebase/index.html`, `codebase/styles.css`, `codebase/app.js` |
| Nguyễn Trọng Tấn | 2A202600901 | Product SPEC, AI Product Canvas, failure modes và demo story | `spec/spec.md`, `AI-flows-and-team-plan.md` |
| Nguyễn Anh Chức | 2A202600617 | Backend gọi AI, validation, xử lý lỗi API, test và hướng dẫn chạy | `codebase/server.py`, `codebase/spending-agent.js`, `codebase/tests/test_server.py`, `codebase/README.md`, `codebase/.env.example` |

### Việc cụ thể trước khi mỗi người commit

| Thành viên | Việc cần kiểm tra hoặc hoàn thiện |
|---|---|
| Nguyễn Thành Lam | Kiểm tra đủ 30 giao dịch; bảo đảm có happy case, low-confidence case và case VINUNI bị phân loại sai; giải thích được vì sao dữ liệu này dùng để test. |
| Trần Văn Quang | Kiểm tra giao diện trước/sau phân loại; nút lọc không làm rỗng hoặc lỗi layout; sửa category phải cập nhật số liệu dashboard. |
| Nguyễn Trọng Tấn | Rà lại SPEC khớp với prototype; chuẩn bị câu trả lời về augment, failure mode chính, bốn đường trải nghiệm và giới hạn correction hiện tại. |
| Nguyễn Anh Chức | Kiểm tra OpenRouter call, schema validation, xử lý lỗi API và unit test; bảo đảm README hướng dẫn chạy đúng. |

