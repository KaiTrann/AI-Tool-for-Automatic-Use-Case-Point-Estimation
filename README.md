# AI Tool for Automatic Use Case Point Estimation

Đây là một prototype học thuật đơn giản cho đồ án môn học về ước lượng Use Case Point (UCP).

Project hiện được thiết kế theo hướng:
- Nhận `Requirements Text` hoặc `Use Case Description` ở dạng plain text
- Có thể nhận thêm nội dung text từ file upload
- Trích xuất `Actor` và `Use Case` trực tiếp từ đoạn mô tả tự nhiên
- Không yêu cầu đầu vào phải theo formal use case specification template

## Ý tưởng chính

- Backend dùng FastAPI với các module nhỏ, dễ đọc và dễ test.
- Frontend dùng React để demo luồng `Extract` và `Calculate`.
- Phần extraction hiện có `mock mode` và `placeholder mode`.
- Kết quả extraction được normalize trước khi tính UCP để giảm lỗi do tên dài, trùng hoặc sai rule.
- Có thêm tài liệu [`PROJECT_STRUCTURE_VI.md`](./PROJECT_STRUCTURE_VI.md) để tra cứu nhanh từng folder và file chính.

## Giải thích nhanh về LLM Mode

- `Mock Mode`
  - Dùng rule-based extraction nội bộ
  - Không gọi LLM thật
  - Phù hợp để demo ổn định trên máy local

- `Placeholder API Mode`
  - Chưa gọi LLM thật, nhưng giữ sẵn vị trí tích hợp
  - Backend vẫn build prompt extraction để mô phỏng kiến trúc tương lai
  - Phù hợp để giải thích rằng hệ thống có thể nâng cấp sang LLM API thật sau này

## Cấu trúc hiện tại

```text
AI Tool for Automatic UCPE/
|-- backend/
|   |-- app/
|   |   |-- api/
|   |   |   |-- routes/
|   |   |   |   |-- analysis.py
|   |   |   |   `-- health.py
|   |   |   `-- router.py
|   |   |-- models/
|   |   |   |-- request_models.py
|   |   |   |-- response_models.py
|   |   |   |-- requests.py
|   |   |   `-- responses.py
|   |   |-- services/
|   |   |   |-- effort_estimation_service.py
|   |   |   |-- llm_extractor.py
|   |   |   |-- prompt_templates.py
|   |   |   |-- schedule_estimation_service.py
|   |   |   `-- ucp_calculator.py
|   |   |-- utils/
|   |   |   |-- file_reader.py
|   |   |   |-- llm_json_parser.py
|   |   |   |-- normalization.py
|   |   |   `-- parser.py
|   |   `-- main.py
|   |-- tests/
|   |   |-- test_api.py
|   |   |-- test_llm_extractor.py
|   |   `-- test_ucp_calculator.py
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   |   |-- api/
|   |   |   `-- client.js
|   |   |-- components/
|   |   |   |-- ActorsTable.jsx
|   |   |   |-- ChartPanel.jsx
|   |   |   |-- ResultCards.jsx
|   |   |   `-- UseCasesTable.jsx
|   |   |-- pages/
|   |   |   `-- HomePage.jsx
|   |   |-- utils/
|   |   |   `-- requestHelpers.js
|   |   |-- styles/
|   |   |   `-- index.css
|   |   |-- App.jsx
|   |   `-- main.jsx
|   |-- index.html
|   |-- package.json
|   `-- vite.config.js
`-- .gitignore
```

## Luồng xử lý

1. Người dùng nhập `Requirements Text` hoặc tải lên file có nội dung text.
2. Backend trích xuất `Actor` và `Use Case` từ free-text input.
3. Kết quả được normalize:
   - bỏ `System` như một actor
   - gộp trùng
   - chuẩn hóa tên use case về dạng ngắn, dễ tính UCP
4. Hệ thống tính:
   - `UAW`
   - `UUCW`
   - `UUCP`
   - `UCP`
   - `Effort`
   - `Schedule`

## Cách chạy

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend mặc định gọi backend tại `http://localhost:8000`.

## Ghi chú

- Phiên bản hiện tại không parse đầy đủ file `.docx` thật.
- Backend có thể đọc tốt file text đơn giản và mock uploaded content có tên `.docx`.
- Mục tiêu của project là UCP estimation từ free-text requirements, không phải sinh hay phân tích đầy đủ Use Case Specification document.
