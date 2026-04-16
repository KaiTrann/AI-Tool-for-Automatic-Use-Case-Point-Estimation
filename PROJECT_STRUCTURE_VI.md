# Bản Đồ Project AI Tool for Automatic UCPE

Tài liệu này giúp bạn tra nhanh:
- project có những folder nào
- từng file chính dùng để làm gì
- khi cần giải thích một chức năng thì nên mở file nào để chứng minh

Lưu ý:
- Tài liệu tập trung vào file source do nhóm viết
- Không đi sâu vào `.venv`, `node_modules`, `__pycache__` vì đó là thư viện hoặc file sinh tự động

## 1. Cấu trúc tổng quát

```text
AI Tool for Automatic UCPE/
├─ README.md
├─ PROJECT_STRUCTURE_VI.md
├─ THUYET_MINH_CODE_VI.md
├─ backend/
│  ├─ requirements.txt
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ api/
│  │  │  ├─ router.py
│  │  │  └─ routes/
│  │  │     ├─ analysis.py
│  │  │     └─ health.py
│  │  ├─ models/
│  │  │  ├─ request_models.py
│  │  │  ├─ response_models.py
│  │  │  ├─ requests.py
│  │  │  └─ responses.py
│  │  ├─ services/
│  │  │  ├─ effort_estimation_service.py
│  │  │  ├─ llm_extractor.py
│  │  │  ├─ mapping_config.py
│  │  │  ├─ prompt_templates.py
│  │  │  ├─ schedule_estimation_service.py
│  │  │  └─ ucp_calculator.py
│  │  └─ utils/
│  │     ├─ file_reader.py
│  │     ├─ llm_json_parser.py
│  │     ├─ normalization.py
│  │     └─ parser.py
│  └─ tests/
│     ├─ test_api.py
│     ├─ test_llm_extractor.py
│     └─ test_ucp_calculator.py
└─ frontend/
   ├─ package.json
   ├─ vite.config.js
   ├─ index.html
   └─ src/
      ├─ App.jsx
      ├─ main.jsx
      ├─ api/
      │  └─ client.js
      ├─ components/
      │  ├─ ActorsTable.jsx
      │  ├─ ChartPanel.jsx
      │  ├─ ResultCards.jsx
      │  └─ UseCasesTable.jsx
      ├─ pages/
      │  └─ HomePage.jsx
      ├─ styles/
      │  └─ index.css
      └─ utils/
         └─ requestHelpers.js
```

## 2. File ở thư mục gốc

- `README.md`
  - Hướng dẫn cài đặt và chạy project trên máy mới.
  - Đây là file nên mở đầu tiên nếu người khác muốn chạy thử hệ thống.

- `PROJECT_STRUCTURE_VI.md`
  - Bản đồ file/folder bằng tiếng Việt.
  - Dùng để tra nhanh “chức năng này nằm ở đâu”.

- `THUYET_MINH_CODE_VI.md`
  - Giải thích luồng chạy từ lúc người dùng nhập dữ liệu đến lúc ra UCP.
  - Hữu ích khi thuyết trình hoặc bảo vệ đồ án.

- `.gitignore`
  - Khai báo các file không nên đưa lên Git như `.venv`, `node_modules`, cache test.

## 3. Backend

### `backend/`

- `requirements.txt`
  - Danh sách thư viện Python cần cài cho backend.
  - Ví dụ: `fastapi`, `uvicorn`, `pydantic`, `pytest`.

### `backend/app/`

Đây là nơi chứa toàn bộ code backend chính.

- `main.py`
  - Điểm khởi động FastAPI.
  - Tạo app, bật CORS, nạp toàn bộ router.
  - Khi chạy `uvicorn app.main:app --reload`, file này được dùng.

### `backend/app/api/`

Chứa phần route API.

- `router.py`
  - Router tổng.
  - Gom các route nhỏ lại để `main.py` include một lần.

### `backend/app/api/routes/`

- `health.py`
  - Chứa endpoint `GET /health`.
  - Frontend dùng để kiểm tra backend còn hoạt động hay không.

- `analysis.py`
  - File route quan trọng nhất của backend.
  - Chứa 3 endpoint chính:
    - `POST /extract`
    - `POST /ucp/calculate`
    - `POST /analyze-and-calculate`
  - Đây là nơi nối toàn bộ pipeline:
    - đọc text
    - đọc file upload
    - gọi extraction
    - gọi UCP calculator
    - trả kết quả về frontend

### `backend/app/models/`

Chứa các model Pydantic để validate request/response.

- `request_models.py`
  - Model cho phần tính UCP lõi.
  - Gồm:
    - `Actor`
    - `UseCase`
    - `UCPRequest`

- `response_models.py`
  - Model response cho phần tính UCP lõi.
  - Gồm:
    - `UCPResponse`

- `requests.py`
  - Model request tổng quát dùng cho API backend.
  - Gồm:
    - `ActorItem`
    - `UseCaseItem`
    - `ExtractRequest`
    - `AnalyzeAndCalculateRequest`
    - `UcpCalculateRequest`

- `responses.py`
  - Model response tổng quát dùng cho API backend.
  - Gồm:
    - `HealthResponse`
    - `ExtractionResponse`
    - `UcpBreakdownResponse`
    - `EffortEstimateResponse`
    - `ScheduleEstimateResponse`
    - `UcpCalculationResponse`
    - `AnalysisAndCalculationResponse`

### `backend/app/services/`

Chứa logic nghiệp vụ chính.

- `llm_extractor.py`
  - Trung tâm của pipeline trích xuất actor và use case.
  - Hỗ trợ 2 kiểu đầu vào:
    - text thường
    - Use Case Document theo template
  - Hỗ trợ 2 mode:
    - `mock`
    - `placeholder`
  - Công việc chính:
    - ghép text nhập tay và text từ file
    - phát hiện đầu vào có phải template hay không
    - trích xuất actor và use case
    - ước lượng complexity ban đầu
    - parse JSON và gọi normalization

- `prompt_templates.py`
  - Chứa prompt mẫu cho placeholder LLM mode.
  - Hiện tại project chưa gọi LLM thật, nhưng file này giữ sẵn prompt để sau này nâng cấp.

- `mapping_config.py`
  - File cấu hình rule quan trọng nhất cho extraction/normalization.
  - Dùng để chỉnh:
    - keyword nhận diện human actor
    - keyword nhận diện external actor
    - danh sách internal step cần loại
    - rule merge use case
    - rule phân loại simple / average / complex
  - Nếu cần sửa rule cho domain mới như banking, hotel, library thì thường sửa ở file này.

- `ucp_calculator.py`
  - Bộ tính UCP cốt lõi.
  - Chứa công thức:
    - actor weight
    - use case weight
    - UAW
    - UUCW
    - UUCP
    - UCP
    - effort estimation

- `effort_estimation_service.py`
  - Tính effort từ UCP.
  - Công thức hiện tại:
    - `effort = UCP * productivity_factor`

- `schedule_estimation_service.py`
  - Tính schedule từ effort.
  - Công thức hiện tại:
    - `schedule = effort_hours / (team_size * 160)`
  - Có làm tròn kiểu `ROUND_HALF_UP` để kết quả demo dễ đọc hơn.

### `backend/app/utils/`

Chứa các hàm hỗ trợ.

- `file_reader.py`
  - Đọc file upload và chuyển thành text.
  - Hiện đang hỗ trợ:
    - `.txt`
    - `.md`
    - `.docx`
    - `.doc` theo kiểu best-effort
  - Nếu người dùng upload Use Case Document dạng Word thì file này là nơi xử lý đầu tiên.

- `llm_json_parser.py`
  - Kiểm tra JSON extractor trả về có đúng schema không.
  - Chuẩn hóa dữ liệu ban đầu trước khi đưa sang normalization.

- `normalization.py`
  - File cực kỳ quan trọng của extraction pipeline.
  - Dùng để:
    - bỏ `System` khỏi actor
    - chuẩn hóa actor human/external
    - đổi use case về dạng `Verb + Noun`
    - giữ đúng domain noun
    - loại internal step
    - gộp sub-action
    - deduplicate
    - phân loại lại complexity
  - Nếu extraction bị sai, gần như chắc chắn cần kiểm tra file này.

- `parser.py`
  - Các helper xử lý text cơ bản.
  - Ví dụ:
    - ghép nhiều nguồn text
    - chuẩn hóa khoảng trắng
    - tách câu

### `backend/tests/`

Chứa test backend.

- `test_api.py`
  - Test các endpoint FastAPI.
  - Dùng để chứng minh API chạy đúng end-to-end.

- `test_llm_extractor.py`
  - Test extraction và normalization.
  - Đây là nơi chứng minh:
    - actor được nhận diện đúng
    - use case không bị sentence fragment
    - internal step bị loại đúng
    - complexity classifier hoạt động đúng theo từng domain

- `test_ucp_calculator.py`
  - Test các công thức UCP, effort, schedule.

## 4. Frontend

### `frontend/`

- `package.json`
  - Danh sách thư viện frontend và script chạy project.
  - Lệnh chính:
    - `npm install`
    - `npm run dev`
    - `npm run build`

- `vite.config.js`
  - Cấu hình Vite cho frontend React.

- `index.html`
  - File HTML gốc để React mount vào.

### `frontend/src/`

- `main.jsx`
  - Điểm khởi động React.

- `App.jsx`
  - App chính, hiện render `HomePage`.

### `frontend/src/pages/`

- `HomePage.jsx`
  - File frontend quan trọng nhất.
  - Chứa giao diện chính:
    - nhập text
    - chọn file `.doc/.docx/.txt`
    - chọn `LLM Mode`
    - bấm `Extract`
    - bấm `Calculate`
    - hiển thị loading, error, success
  - Đây là nơi điều phối gọi API và cập nhật state kết quả.

### `frontend/src/api/`

- `client.js`
  - Gom tất cả lệnh gọi backend vào một nơi.
  - Chứa:
    - `checkHealth()`
    - `extractData()`
    - `calculateUCP()`
    - `analyzeAndCalculate()`
  - Nếu frontend báo lỗi gọi API, nên kiểm tra file này trước.

### `frontend/src/utils/`

- `requestHelpers.js`
  - Các hàm hỗ trợ tạo payload.
  - Ví dụ:
    - tạo chữ ký input để biết extraction cũ còn dùng được không
    - build payload gửi sang `/ucp/calculate`

### `frontend/src/components/`

- `ActorsTable.jsx`
  - Hiển thị bảng actor.

- `UseCasesTable.jsx`
  - Hiển thị bảng use case.

- `ResultCards.jsx`
  - Hiển thị các card kết quả:
    - UAW
    - UUCW
    - UCP
    - Effort
    - Schedule

- `ChartPanel.jsx`
  - Hiển thị biểu đồ Chart.js cho phân bố độ phức tạp của actor và use case.

### `frontend/src/styles/`

- `index.css`
  - Toàn bộ CSS chính của giao diện.

## 5. Giải thích nhanh về LLM Mode

### `Mock Mode`

- Không gọi AI thật.
- Backend dùng extractor rule-based nội bộ.
- Phù hợp để demo ổn định trên lớp vì:
  - không cần API key
  - không phụ thuộc Internet
  - kết quả nhất quán hơn

### `Placeholder API Mode`

- Chưa gọi AI thật, nhưng giữ sẵn kiến trúc để sau này nối LLM API.
- Backend vẫn build prompt và đi qua pipeline như khi tích hợp thật.
- Mục đích:
  - chứng minh project có hướng mở rộng AI
  - nhưng hiện tại vẫn chạy ổn định cho demo sinh viên

## 6. Khi bị hỏi “chức năng này nằm ở đâu?”

- Muốn giải thích route API:
  - `backend/app/api/routes/analysis.py`

- Muốn giải thích logic extract actor/use case:
  - `backend/app/services/llm_extractor.py`

- Muốn giải thích rule normalize và complexity:
  - `backend/app/utils/normalization.py`
  - `backend/app/services/mapping_config.py`

- Muốn giải thích cách đọc file `.docx/.doc`:
  - `backend/app/utils/file_reader.py`

- Muốn giải thích công thức UCP:
  - `backend/app/services/ucp_calculator.py`

- Muốn giải thích effort và schedule:
  - `backend/app/services/effort_estimation_service.py`
  - `backend/app/services/schedule_estimation_service.py`

- Muốn giải thích frontend gọi backend thế nào:
  - `frontend/src/api/client.js`

- Muốn giải thích nút `Extract` và `Calculate`:
  - `frontend/src/pages/HomePage.jsx`

- Muốn chứng minh project có test:
  - `backend/tests/test_api.py`
  - `backend/tests/test_llm_extractor.py`
  - `backend/tests/test_ucp_calculator.py`
