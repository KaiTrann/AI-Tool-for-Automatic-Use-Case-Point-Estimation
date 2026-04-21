# PROJECT_STRUCTURE_VI

Tài liệu này giúp bạn tra nhanh:
- project có những folder nào
- từng file chính dùng để làm gì
- khi bị hỏi một chức năng nào đó thì nên mở file nào để giải thích

Lưu ý:
- tài liệu chỉ tập trung vào source code chính
- không đi sâu vào `.venv`, `node_modules`, `__pycache__`

## 1. Cấu trúc tổng quát

```text
AI Tool for Automatic UCPE/
├─ README.md
├─ PROJECT_STRUCTURE_VI.md
├─ THUYET_MINH_CODE_VI.md
├─ backend/
│  ├─ requirements.txt
│  ├─ app/
│  └─ tests/
└─ frontend/
   ├─ package.json
   ├─ vite.config.js
   └─ src/
```

## 2. Thư mục gốc

### `README.md`

Công dụng:
- hướng dẫn cài và chạy project
- giải thích chuẩn UCP đang áp dụng
- giải thích `LLM Mode`

Khi nào mở file này:
- khi người khác mới cầm project
- khi cần hướng dẫn chạy trên máy lạ

### `PROJECT_STRUCTURE_VI.md`

Công dụng:
- bản đồ file/folder bằng tiếng Việt

### `THUYET_MINH_CODE_VI.md`

Công dụng:
- giải thích luồng chạy từ lúc nhập dữ liệu đến lúc ra UCP

## 3. Backend tổng quan

```text
backend/
├─ requirements.txt
├─ app/
│  ├─ main.py
│  ├─ api/
│  ├─ models/
│  ├─ services/
│  └─ utils/
└─ tests/
```

### `backend/requirements.txt`

Công dụng:
- liệt kê thư viện Python cần cài cho backend

Ví dụ:
- `fastapi`
- `uvicorn`
- `pydantic`
- `pytest`
- `python-multipart`

## 4. Backend app

### `backend/app/main.py`

Công dụng:
- điểm khởi động FastAPI
- tạo app
- bật CORS
- include router

Khi chạy:

```powershell
uvicorn app.main:app --reload
```

thì file này được dùng.

## 5. API layer

```text
backend/app/api/
├─ router.py
└─ routes/
   ├─ analysis.py
   └─ health.py
```

### `backend/app/api/router.py`

Công dụng:
- gom các route nhỏ thành router tổng

### `backend/app/api/routes/health.py`

Công dụng:
- chứa endpoint `GET /health`
- giúp kiểm tra backend còn hoạt động hay không

### `backend/app/api/routes/analysis.py`

Công dụng:
- route quan trọng nhất của backend
- chứa 3 endpoint chính:
  - `POST /extract`
  - `POST /ucp/calculate`
  - `POST /analyze-and-calculate`

Chức năng:
- nhận text và file upload
- gọi extraction service
- gọi UCP calculator
- trả kết quả cho frontend

Khi nào mở file này:
- khi cần giải thích backend nhận request như thế nào
- khi cần chứng minh luồng “extract rồi calculate”

## 6. Models layer

```text
backend/app/models/
├─ request_models.py
├─ response_models.py
├─ requests.py
└─ responses.py
```

### `backend/app/models/request_models.py`

Công dụng:
- model Pydantic cho module tính UCP lõi

File này chứa:
- `Actor`
- `UseCase`
- `UCPRequest`

### `backend/app/models/response_models.py`

Công dụng:
- model Pydantic cho output của module UCP lõi

File này chứa:
- `UCPResponse`

### `backend/app/models/requests.py`

Công dụng:
- model request dùng cho API

File này chứa:
- `ActorItem`
- `UseCaseItem`
- `ExtractRequest`
- `AnalyzeAndCalculateRequest`
- `UcpCalculateRequest`
- `NormalizedUseCaseDocument`

### `backend/app/models/responses.py`

Công dụng:
- model response dùng cho API

File này chứa:
- `HealthResponse`
- `ExtractionResponse`
- `UcpCalculationResponse`
- `AnalysisAndCalculationResponse`
- các response con cho effort, schedule, breakdown

## 7. Services layer

```text
backend/app/services/
├─ actor_classifier.py
├─ effort_estimation_service.py
├─ llm_extractor.py
├─ mapping_config.py
├─ prompt_templates.py
├─ schedule_estimation_service.py
├─ ucp_calculator.py
└─ use_case_classifier.py
```

### `backend/app/services/llm_extractor.py`

Công dụng:
- file điều phối chính của extraction pipeline

Chức năng:
- ghép text nhập tay và text từ file
- kiểm tra input là free-text hay tài liệu có cấu trúc
- nếu là tài liệu có cấu trúc thì parse theo document parser
- nếu là free-text thì extract actor/use case thô
- trả kết quả đã chuẩn hóa về API

Đây là nơi `LLM Mode` có tác dụng trực tiếp.

### `backend/app/services/prompt_templates.py`

Công dụng:
- chứa prompt mẫu cho `Placeholder API Mode`

Chức năng:
- chuẩn bị prompt sẵn cho hướng tích hợp LLM API thật sau này

### `backend/app/services/mapping_config.py`

Công dụng:
- chứa rule, keyword, merge rule cho normalization/classification

Khi nào sửa file này:
- khi cần thêm từ khóa actor
- khi cần thêm pattern loại internal step
- khi cần điều chỉnh merge rule

### `backend/app/services/actor_classifier.py`

Công dụng:
- phân loại actor theo chuẩn UCP

Logic chính:
- `simple`: external system / API rõ ràng
- `average`: file / database / protocol / text interface
- `complex`: human actor dùng GUI

### `backend/app/services/use_case_classifier.py`

Công dụng:
- phân loại use case theo transaction count

Logic chính:
- `<= 3 transactions` -> `simple`
- `4–7 transactions` -> `average`
- `> 7 transactions` -> `complex`

Lưu ý:
- với tài liệu có cấu trúc, file này quan trọng hơn rule keyword

### `backend/app/services/ucp_calculator.py`

Công dụng:
- module tính UCP lõi

Chức năng:
- tính actor weight
- tính use case weight
- tính `UAW`
- tính `UUCW`
- tính `UUCP`
- tính `UCP`

### `backend/app/services/effort_estimation_service.py`

Công dụng:
- tính effort từ `UCP`

Công thức:

```text
Effort = UCP * productivity_factor
```

### `backend/app/services/schedule_estimation_service.py`

Công dụng:
- tính schedule từ effort

Công thức:

```text
Schedule = effort_hours / (team_size * 160)
```

## 8. Utils layer

```text
backend/app/utils/
├─ actor_normalizer.py
├─ field_aliases.py
├─ file_reader.py
├─ llm_json_parser.py
├─ normalization.py
├─ parser.py
├─ use_case_document_parser.py
└─ use_case_extractor.py
```

### `backend/app/utils/file_reader.py`

Công dụng:
- đọc file upload và chuyển thành text

Hiện hỗ trợ:
- `.txt`
- `.md`
- `.docx`
- `.doc` theo kiểu best-effort

### `backend/app/utils/parser.py`

Công dụng:
- các helper xử lý text cơ bản

Ví dụ:
- ghép nhiều nguồn text
- chuẩn hóa khoảng trắng
- tách câu

### `backend/app/utils/llm_json_parser.py`

Công dụng:
- parse và validate JSON extraction

Vai trò:
- đảm bảo schema JSON đúng trước khi đưa sang normalization

### `backend/app/utils/use_case_document_parser.py`

Công dụng:
- parser rule-based cho SRS / Use Case Document
- hỗ trợ thêm template IEEE 830-1998 style SRS như HR/Payroll Dashboard

Chức năng:
- bỏ qua table of contents, metadata, revision history
- đọc `5.2 List of Use Case`
- đọc `5.4 Use Case Specification`
- merge dữ liệu list và block chi tiết bằng `Use Case ID`
- tách đúng từng block `UC.xx`
- đọc các field như `Use Case Name`, `Actors`, `Main Flow`
- tách step để phục vụ đếm transaction

Khi nào mở file này:
- khi bị hỏi tại sao project đọc được `.docx` template
- khi cần chứng minh parser không lấy nhầm mục lục
- khi cần chứng minh project đọc được file IEEE/HR thật

### `backend/app/utils/field_aliases.py`

Công dụng:
- khai báo alias field và section cho nhiều template SRS khác nhau

Ví dụ alias đang hỗ trợ:
- `Brief Description` / `Description`
- `Goal` / `Objective`
- `Pre-condition` / `Pre-conditions` / `Preconditions`
- `Main Flow` / `Main Success Scenario`
- `Alternative Flow` / `Alternative Scenario`
- `Exception Flow` / `Exception`
- `Business Rule` / `Business Rules`

Khi nào mở file này:
- khi file SRS thật có tên field khác template hiện tại
- khi muốn thêm template mới mà không sửa nhiều logic parser

### `backend/app/utils/actor_normalizer.py`

Công dụng:
- làm sạch danh sách actor lấy từ tài liệu

Ví dụ xử lý:
- bỏ prefix như `Including:`
- tách danh sách actor phân cách bằng dấu phẩy
- chuẩn hóa tên actor

### `backend/app/utils/use_case_extractor.py`

Công dụng:
- lấy tên use case đúng từ tài liệu có cấu trúc

Ưu tiên:
1. `Use case name`
2. nếu thiếu thì fallback về header `UC 01: Login`

### `backend/app/utils/normalization.py`

Công dụng:
- lớp làm sạch dữ liệu quan trọng nhất trước khi tính UCP

Chức năng:
- bỏ actor `System`
- bỏ trùng actor/use case
- chuẩn hóa tên actor
- chuẩn hóa tên use case
- loại internal step
- merge sub-action nếu cần
- chuẩn hóa complexity

Khi nào mở file này:
- khi extraction ra sai tên
- khi có use case thừa
- khi bị hỏi vì sao một actor/use case bị loại bỏ

## 9. Test layer

```text
backend/tests/
├─ test_api.py
├─ test_llm_extractor.py
└─ test_ucp_calculator.py
```

### `backend/tests/test_api.py`

Công dụng:
- test endpoint backend theo kiểu end-to-end

### `backend/tests/test_llm_extractor.py`

Công dụng:
- test parser, extraction, normalization, classifier

Đây là nơi kiểm tra các domain như:
- e-commerce
- library
- hotel
- banking

### `backend/tests/test_ucp_calculator.py`

Công dụng:
- test công thức UCP
- test effort
- test schedule

## 10. Frontend tổng quan

```text
frontend/
├─ package.json
├─ vite.config.js
├─ index.html
└─ src/
   ├─ App.jsx
   ├─ main.jsx
   ├─ api/
   ├─ components/
   ├─ pages/
   ├─ styles/
   └─ utils/
```

### `frontend/package.json`

Công dụng:
- khai báo dependency và script frontend

### `frontend/vite.config.js`

Công dụng:
- cấu hình Vite

### `frontend/src/main.jsx`

Công dụng:
- điểm khởi động React

### `frontend/src/App.jsx`

Công dụng:
- app gốc, render `HomePage`

## 11. Frontend API

### `frontend/src/api/client.js`

Công dụng:
- gom tất cả lệnh gọi API về một chỗ

Các hàm chính:
- `checkHealth()`
- `extractData()`
- `calculateUCP()`
- `analyzeAndCalculate()`

## 12. Frontend page chính

### `frontend/src/pages/HomePage.jsx`

Công dụng:
- giao diện chính của project

Chức năng:
- nhập text
- upload file
- chọn `LLM Mode`
- bấm `Extract`
- bấm `Calculate`
- hiển thị loading, error, success

## 13. Frontend components

### `frontend/src/components/ActorsTable.jsx`

Công dụng:
- hiển thị bảng actor

### `frontend/src/components/UseCasesTable.jsx`

Công dụng:
- hiển thị bảng use case

### `frontend/src/components/ResultCards.jsx`

Công dụng:
- hiển thị `UAW`, `UUCW`, `UCP`, `Effort`, `Schedule`

### `frontend/src/components/ChartPanel.jsx`

Công dụng:
- hiển thị biểu đồ phân bố complexity bằng Chart.js

## 14. Frontend helper

### `frontend/src/utils/requestHelpers.js`

Công dụng:
- tạo payload gửi backend
- so khớp chữ ký input để biết có cần extract lại không

## 15. Khi bị hỏi “muốn giải thích chức năng này thì mở file nào?”

- Route backend:
  - `backend/app/api/routes/analysis.py`

- Parser tài liệu SRS / use case document:
  - `backend/app/utils/use_case_document_parser.py`
  - `backend/app/utils/field_aliases.py`

- Trích xuất actor/use case:
  - `backend/app/services/llm_extractor.py`

- Làm sạch và chuẩn hóa:
  - `backend/app/utils/normalization.py`

- Phân loại actor theo chuẩn UCP:
  - `backend/app/services/actor_classifier.py`

- Phân loại use case theo transaction count:
  - `backend/app/services/use_case_classifier.py`

- Công thức UCP:
  - `backend/app/services/ucp_calculator.py`

- Giao diện chính:
  - `frontend/src/pages/HomePage.jsx`

- Gọi API từ frontend:
  - `frontend/src/api/client.js`
