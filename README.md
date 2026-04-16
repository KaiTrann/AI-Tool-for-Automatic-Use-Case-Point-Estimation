# AI Tool for Automatic Use Case Point Estimation

Đây là prototype học thuật dùng để:
- nhận `Requirements Text`
- nhận `Use Case Description`
- hoặc nhận file `Use Case Document / SRS` upload lên
- trích xuất `Actor`, `Use Case`
- tính `UAW`, `UUCW`, `UUCP`, `UCP`, `Effort`, `Schedule`

Project phù hợp cho demo sinh viên vì:
- code đơn giản, tách module rõ
- không dùng database
- không dùng authentication phức tạp
- có thể demo bằng text thường hoặc file `.docx`

## 1. Công nghệ sử dụng

- Backend: `FastAPI` + `Python`
- Frontend: `React` + `Vite`
- Visualization: `Chart.js`
- Test backend: `pytest`

## 2. Chuẩn UCP đang áp dụng trong project

### Actor complexity theo chuẩn UCP

- `simple = 1`
- `average = 2`
- `complex = 3`

Ý nghĩa:
- `simple actor`: hệ thống ngoài có API rõ ràng
- `average actor`: giao tiếp qua file / database / protocol / text interface
- `complex actor`: người dùng thao tác qua GUI

### Use case complexity theo chuẩn UCP

- `simple = <= 3 transactions`
- `average = 4–7 transactions`
- `complex = > 7 transactions`

### Use case weight trong UUCW

- `simple = 5`
- `average = 10`
- `complex = 15`

### Công thức đang dùng

- `UAW = tổng trọng số actor`
- `UUCW = tổng trọng số use case`
- `UUCP = UAW + UUCW`
- `UCP = UUCP * TCF * ECF`
- `Effort = UCP * productivity_factor`
- `Schedule (tháng) = effort_hours / (team_size * 160)`

## 3. Project hiện hỗ trợ input gì

Hệ thống hiện hỗ trợ 2 kiểu input:

### Kiểu 1: văn bản tự do

Ví dụ:
- requirements text
- mô tả use case ngắn
- đoạn mô tả nghiệp vụ dạng paragraph

### Kiểu 2: Use Case Document / SRS có cấu trúc

Hệ thống hiện đã hỗ trợ đọc nội dung từ:
- `.txt`
- `.md`
- `.docx`
- `.doc` theo kiểu best-effort

Nếu tài liệu có các mục như:
- `Use Case ID`
- `Use Case Name`
- `Actors`
- `Description`
- `Pre-conditions`
- `Post-conditions`
- `Main Flow`
- `Alternative Flow`

thì backend sẽ ưu tiên parse theo cấu trúc tài liệu, không đoán kiểu free-text nữa.

## 4. Cấu trúc thư mục chính

```text
AI Tool for Automatic UCPE/
├─ backend/
├─ frontend/
├─ README.md
├─ PROJECT_STRUCTURE_VI.md
└─ THUYET_MINH_CODE_VI.md
```

Tài liệu đi kèm:
- [PROJECT_STRUCTURE_VI.md](./PROJECT_STRUCTURE_VI.md): giải thích từng folder, từng file chính
- [THUYET_MINH_CODE_VI.md](./THUYET_MINH_CODE_VI.md): giải thích luồng chạy từ input đến UCP

## 5. Yêu cầu môi trường trên máy mới

Cần cài:

1. `Python 3.12` hoặc `Python 3.13`
2. `Node.js 18+`
3. `npm`

Khuyến khích cài thêm:

4. `Git`
5. `VS Code`

Kiểm tra nhanh:

```powershell
python --version
node --version
npm --version
```

## 6. Nguyên tắc tránh xung đột môi trường

### Backend Python

Luôn dùng virtual environment riêng của project:

```text
backend/.venv
```

Không nên cài package bằng `pip` global.

Luôn ưu tiên:

```powershell
python -m pip install ...
```

thay vì:

```powershell
pip install ...
```

### Frontend Node

Frontend chỉ nên cài package trong:

```text
frontend/node_modules
```

Không copy `node_modules` từ project khác sang.

## 7. Cài backend từ đầu

Mở PowerShell:

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Sau khi chạy thành công:
- backend ở `http://127.0.0.1:8000`
- Swagger ở `http://127.0.0.1:8000/docs`
- health check ở `http://127.0.0.1:8000/health`

## 8. Cài frontend từ đầu

Mở terminal mới:

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\frontend"
npm install
npm run dev
```

Sau khi chạy thành công:
- frontend ở `http://localhost:5173`

## 9. Cách chạy project đầy đủ

Cần 2 terminal:

### Terminal 1: backend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Terminal 2: frontend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\frontend"
npm run dev
```

Sau đó mở:

```text
http://localhost:5173
```

## 10. Cách chạy test

### Backend test

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

### Frontend build

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\frontend"
npm run build
```

## 11. LLM Mode là gì

Trên frontend có 2 lựa chọn:

### `Mock Mode`

Công dụng cụ thể:
- không gọi AI thật
- dùng extractor rule-based trong backend
- cho kết quả ổn định khi demo
- không cần API key
- phù hợp khi thầy/cô hỏi demo offline

### `Placeholder API Mode`

Công dụng cụ thể:
- giữ sẵn vị trí tích hợp LLM API thật
- backend vẫn build prompt nội bộ
- giúp giải thích kiến trúc AI của project
- hiện tại vẫn fallback về extractor nội bộ để tránh lỗi demo

Nói ngắn gọn:
- `Mock Mode` dùng để demo ổn định
- `Placeholder API Mode` dùng để chứng minh kiến trúc có thể mở rộng sang LLM thật

File liên quan:
- `backend/app/services/llm_extractor.py`
- `backend/app/services/prompt_templates.py`
- `frontend/src/pages/HomePage.jsx`

## 12. Luồng xử lý backend hiện tại

Luồng tổng quát:

1. Frontend gửi text hoặc file lên API.
2. Backend đọc file bằng `file_reader.py`.
3. `llm_extractor.py` kiểm tra input là free-text hay Use Case Document.
4. Nếu là tài liệu có cấu trúc:
   - parse bằng `use_case_document_parser.py`
   - chuẩn hóa bằng `normalization.py`
   - phân loại actor bằng `actor_classifier.py`
   - phân loại use case theo transaction count bằng `use_case_classifier.py`
5. Nếu là free-text:
   - extractor tách actor/use case thô
   - normalization làm sạch, bỏ trùng, bỏ internal step
6. `analysis.py` chuyển dữ liệu sạch sang `ucp_calculator.py`
7. Hệ thống tính `UCP`, `Effort`, `Schedule`
8. Frontend hiển thị bảng, card, biểu đồ

## 13. Các file quan trọng nên biết

- `backend/app/api/routes/analysis.py`
  - route chính của `/extract`, `/ucp/calculate`, `/analyze-and-calculate`

- `backend/app/services/llm_extractor.py`
  - điều phối luồng extraction

- `backend/app/utils/use_case_document_parser.py`
  - parser tài liệu SRS / Use Case Document

- `backend/app/utils/normalization.py`
  - lớp làm sạch dữ liệu trước khi tính UCP

- `backend/app/services/actor_classifier.py`
  - phân loại actor theo chuẩn UCP

- `backend/app/services/use_case_classifier.py`
  - phân loại use case theo transaction count

- `backend/app/services/ucp_calculator.py`
  - công thức UCP lõi

- `frontend/src/pages/HomePage.jsx`
  - giao diện chính

## 14. Lỗi thường gặp

### Lỗi `No module named fastapi`

Cách xử lý:

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Lỗi PowerShell không cho activate

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Lỗi frontend không gọi được backend

Kiểm tra:
- backend đã chạy chưa
- `http://localhost:8000/health` có trả `status: ok` không

### Lỗi môi trường frontend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\frontend"
Remove-Item -Recurse -Force node_modules
npm install
```

## 15. Ghi chú cuối

Project này hiện:
- ưu tiên dễ đọc, dễ demo, dễ giải thích
- không tối ưu theo hướng production phức tạp
- có comment tiếng Việt ở các file logic mới để dễ học và dễ bảo vệ đồ án

Nếu cần hiểu rõ từng file:
- xem [PROJECT_STRUCTURE_VI.md](./PROJECT_STRUCTURE_VI.md)

Nếu cần thuyết trình luồng chạy:
- xem [THUYET_MINH_CODE_VI.md](./THUYET_MINH_CODE_VI.md)
