# AI Tool for Automatic Use Case Point Estimation

Đây là prototype học thuật dùng để:
- nhận `Requirements Text`
- nhận `Use Case Description`
- hoặc nhận file `Use Case Document / SRS` upload lên
- trích xuất `Actor`, `Use Case`
- tính `UAW`, `UUCW`, `UUCP`, `UCP`, `Effort`, `Schedule`

Project phù hợp cho demo sinh viên vì:
- code đơn giản, tách module rõ
- có lưu kết quả vào MySQL sau khi extract/tính UCP
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

Các template đang được hỗ trợ:
- SRS / Use Case Document kiểu cũ của project
- IEEE 830-1998 style SRS, ví dụ file HR/Payroll có `5.2 List of Use Case` và `5.4 Use Case Specification`

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

Với template IEEE/HR thật, parser sẽ:
- đọc `5.2 List of Use Case` để lấy index use case cấp cao
- đọc `5.4 Use Case Specification` để lấy actor, flow, transaction count
- merge hai phần bằng `Use Case ID`
- nếu một use case chỉ có trong list nhưng chưa có block chi tiết, hệ thống vẫn giữ use case đó và dùng fallback heuristic cho complexity

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
   - đọc alias field bằng `field_aliases.py`
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
  - parser tài liệu SRS / Use Case Document, bao gồm template IEEE 830-1998 HR/Payroll

- `backend/app/utils/field_aliases.py`
  - khai báo alias field/section như `Brief Description`, `Goal`, `Main Flow`, `Alternative Flow`, `Business Rule`

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

## 15. Lưu kết quả vào MySQL

Project hiện có persistence đơn giản để lưu kết quả demo sau khi backend extract actor/use case và tính UCP.

Thông tin database mặc định:

```text
Host: localhost
Port: 3307
Username: khanh
Password: khanhcute2306
Database: ucpdb
```

Các bảng chính:

- `documents`: lưu input gốc, tên file upload, loại input.
- `analysis_runs`: lưu một lần chạy phân tích/tính toán.
- `parsed_use_case_documents`: lưu Use Case Document đã parse/normalize.
- `extracted_actors`: lưu actor đã trích xuất.
- `extracted_use_cases`: lưu use case đã trích xuất.
- `calculations`: lưu UAW, UUCW, UUCP, UCP, Effort, Schedule.
- `run_logs`: lưu log từng bước như file_read, parser, extract, normalize, calculate.

### Cài package MySQL cho backend

Package đã nằm trong `backend/requirements.txt`, nên trên máy mới chỉ cần:

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu muốn cài riêng:

```powershell
python -m pip install mysql-connector-python
```

### Tạo database và bảng

Mở MySQL bằng user `root` hoặc user có quyền tạo database:

```powershell
mysql -h localhost -P 3307 -u khanh -p
```

Sau đó nhập password `khanhcute2306`.

Nếu database chưa có, chạy:

```sql
CREATE DATABASE IF NOT EXISTS ucpdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Thoát MySQL rồi chạy schema:

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
mysql -h localhost -P 3307 -u khanh -p ucpdb < database\schema.sql
```

### Biến môi trường nếu đổi cấu hình MySQL

Nếu máy khác dùng tài khoản khác, có thể set trước khi chạy backend:

```powershell
$env:UCP_DB_HOST="localhost"
$env:UCP_DB_PORT="3307"
$env:UCP_DB_USER="khanh"
$env:UCP_DB_PASSWORD="khanhcute2306"
$env:UCP_DB_NAME="ucpdb"
uvicorn app.main:app --reload
```

### Cách kiểm tra dữ liệu đã lưu

1. Chạy backend và frontend như bình thường.
2. Nhập text hoặc upload file `.docx`.
3. Bấm analyze/calculate trên giao diện.
4. Mở Swagger tại `http://127.0.0.1:8000/docs`.
5. Gọi `GET /analysis-runs` để xem danh sách lần chạy đã lưu.
6. Gọi `GET /analysis-runs/{run_id}` để xem chi tiết document, actors, use cases, calculation và logs.
7. Gọi `DELETE /analysis-runs/{run_id}` hoặc bấm nút **Xóa** ở frontend để xóa một kết quả lịch sử.

Ghi chú: nếu MySQL chưa bật, backend vẫn cố gắng giữ API extraction/UCP chạy như cũ để không làm hỏng demo. Khi cần kiểm tra chức năng lưu, hãy đảm bảo MySQL đang chạy và đã chạy `database/schema.sql`.

### Lịch sử tính toán trên frontend

Frontend có mục **Lịch Sử Tính Toán** ở cuối trang:

- **Tải Lại**: gọi `GET /analysis-runs` để lấy các kết quả đã lưu.
- **Xem Lại**: gọi `GET /analysis-runs/{run_id}` rồi đưa actor, use case, UCP, effort, schedule lên lại bảng/card.
- **Xóa**: gọi `DELETE /analysis-runs/{run_id}` để xóa một run khỏi lịch sử.

Khi xóa một `analysis_run`, MySQL tự xóa dữ liệu liên quan trong các bảng con nhờ `ON DELETE CASCADE`.

### Lưu ý về `raw_text`

Endpoint `/ucp/calculate` chỉ nhận actor/use case đã có sẵn, nên có thể không có input text gốc.
Vì vậy backend đã xử lý `raw_text` rỗng an toàn và `database/schema.sql` cũng có migration:

```sql
ALTER TABLE documents
  MODIFY raw_text LONGTEXT NULL;
```

Nếu máy đã từng tạo database từ phiên bản cũ, hãy chạy lại `database/schema.sql` hoặc chạy riêng câu `ALTER TABLE` trên để tránh lỗi tính được nhưng không lưu được calculation.

## 16. Ghi chú cuối

Project này hiện:
- ưu tiên dễ đọc, dễ demo, dễ giải thích
- không tối ưu theo hướng production phức tạp
- có comment tiếng Việt ở các file logic mới để dễ học và dễ bảo vệ đồ án

Nếu cần hiểu rõ từng file:
- xem [PROJECT_STRUCTURE_VI.md](./PROJECT_STRUCTURE_VI.md)

Nếu cần thuyết trình luồng chạy:
- xem [THUYET_MINH_CODE_VI.md](./THUYET_MINH_CODE_VI.md)
