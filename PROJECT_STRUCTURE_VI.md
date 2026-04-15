# Bản Đồ Project AI Tool for Automatic UCPE

Tài liệu này giúp tra nhanh:
- folder nào dùng để làm gì
- file nào chứa logic gì
- khi cần giải thích hoặc chứng minh một chức năng thì nên mở file nào

Lưu ý:
- Tài liệu này tập trung vào file nguồn do nhóm tự viết
- Không đi sâu vào `node_modules`, `.venv`, `.pytest_cache` vì đó là thư viện/phần sinh tự động

## 1. Tổng quan thư mục

### Thư mục gốc

- `README.md`
  - Giới thiệu project, cách chạy backend/frontend, mô tả ý tưởng chung

- `PROJECT_STRUCTURE_VI.md`
  - Tài liệu bản đồ project bằng tiếng Việt

- `.gitignore`
  - Khai báo file/thư mục không nên đưa lên Git

## 2. Backend

### `backend/`

- `requirements.txt`
  - Danh sách thư viện Python cần cài cho backend
  - Ví dụ: FastAPI, Uvicorn, Pydantic, Pytest

### `backend/app/`

Đây là thư mục code backend chính.

- `main.py`
  - Điểm khởi động của FastAPI
  - Tạo app, bật CORS, nạp toàn bộ router API
  - Khi chạy `uvicorn app.main:app --reload` thì file này được dùng

### `backend/app/api/`

Chứa lớp route API.

- `router.py`
  - Router tổng
  - Gom các route nhỏ (`health`, `analysis`) lại để `main.py` include một lần

- `__init__.py`
  - Đánh dấu đây là package Python

### `backend/app/api/routes/`

Chứa các endpoint cụ thể.

- `health.py`
  - API `GET /health`
  - Dùng để frontend kiểm tra backend có đang hoạt động hay không

- `analysis.py`
  - File API quan trọng nhất của backend
  - Chứa:
    - `POST /extract`
    - `POST /ucp/calculate`
    - `POST /analyze-and-calculate`
  - Đây là nơi nối:
    - đọc input text/file
    - gọi extraction service
    - normalize dữ liệu
    - tính UCP, Effort, Schedule

### `backend/app/models/`

Chứa các model dữ liệu Pydantic.

- `request_models.py`
  - Model cho bộ tính UCP core
  - Chứa:
    - `Actor`
    - `UseCase`
    - `UCPRequest`
  - Dùng ở tầng service tính toán

- `response_models.py`
  - Model response cho bộ tính UCP core
  - Chứa `UCPResponse`

- `requests.py`
  - Model request chính của backend API
  - Chứa:
    - `ActorItem`
    - `UseCaseItem`
    - `ExtractRequest`
    - `AnalyzeAndCalculateRequest`
    - `UcpCalculateRequest`
  - Dùng ở tầng route và extraction pipeline

- `responses.py`
  - Model response chính của backend API
  - Chứa:
    - `HealthResponse`
    - `ExtractionResponse`
    - `UcpBreakdownResponse`
    - `EffortEstimateResponse`
    - `ScheduleEstimateResponse`
    - `UcpCalculationResponse`
    - `AnalysisAndCalculationResponse`

- `__init__.py`
  - Đánh dấu package Python

### `backend/app/services/`

Chứa logic nghiệp vụ chính.

- `llm_extractor.py`
  - Trung tâm của luồng trích xuất Actor và Use Case
  - Có 2 mode:
    - `mock`
    - `placeholder`
  - Công việc chính:
    - ghép text đầu vào
    - chọn mode extraction
    - parse JSON extraction
    - gọi normalization
    - trả kết quả cuối cùng cho route

- `prompt_templates.py`
  - Chứa prompt mẫu cho LLM
  - Dùng cho `placeholder mode`
  - Hiện tại chưa gọi model thật nhưng đã có prompt sẵn để dễ nâng cấp sau này

- `mapping_config.py`
  - Cấu hình rule/mapping cho normalization
  - Đây là file rất quan trọng nếu cần chỉnh:
    - từ khóa actor người dùng
    - từ khóa external actor
    - rule merge use case
    - rule classify complexity
    - danh sách internal step cần loại bỏ

- `ucp_calculator.py`
  - Bộ tính UCP cốt lõi
  - Chứa công thức:
    - actor weight
    - use case weight
    - UAW
    - UUCW
    - UUCP
    - UCP
    - effort estimation

- `effort_estimation_service.py`
  - Tính Effort từ UCP
  - Công thức hiện tại:
    - `effort = UCP * productivity_factor`

- `schedule_estimation_service.py`
  - Tính Schedule từ Effort
  - Công thức hiện tại:
    - `schedule = effort_hours / (team_size * 160)`

- `__init__.py`
  - Đánh dấu package Python

### `backend/app/utils/`

Chứa các hàm tiện ích hỗ trợ pipeline.

- `normalization.py`
  - File quan trọng bậc nhất của extraction pipeline
  - Dùng để:
    - bỏ `System` khỏi actor
    - chuẩn hóa actor
    - chuẩn hóa use case về dạng `Verb + Noun`
    - loại internal step
    - merge sub-action thành use case cha
    - deduplicate
    - phân loại lại complexity
  - Nếu extraction sai tên hoặc sai complexity thì gần như chắc chắn phải xem file này

- `llm_json_parser.py`
  - Kiểm tra JSON do extractor trả về có đúng schema hay không
  - Chuẩn hóa dữ liệu ban đầu trước khi vào normalization

- `parser.py`
  - Các helper xử lý text cơ bản
  - Ví dụ:
    - ghép text nhập tay + text từ file
    - tách câu
    - chuẩn hóa khoảng trắng

- `file_reader.py`
  - Đọc file upload và biến thành text
  - Prototype hiện tại chủ yếu hỗ trợ đọc text đơn giản

- `__init__.py`
  - Đánh dấu package Python

### `backend/tests/`

Chứa test backend.

- `test_api.py`
  - Test endpoint FastAPI
  - Khi cần chứng minh API chạy đúng thì mở file này

- `test_llm_extractor.py`
  - Test extraction + normalization
  - Khi cần chứng minh:
    - actor không bị sai
    - use case không bị fragment
    - complexity rule chạy đúng
  - Đây là file nên mở đầu tiên nếu thầy/cô hỏi về extraction logic

- `test_ucp_calculator.py`
  - Test công thức UCP, Effort, Schedule
  - Khi cần chứng minh công thức đúng thì mở file này

## 3. Frontend

### `frontend/`

- `package.json`
  - Khai báo thư viện frontend và script chạy project
  - Các lệnh chính:
    - `npm run dev`
    - `npm run build`

- `package-lock.json`
  - File lock version thư viện của npm

- `index.html`
  - File HTML gốc để React mount vào

- `vite.config.js`
  - Cấu hình Vite

### `frontend/src/`

Chứa mã nguồn React.

- `main.jsx`
  - Điểm khởi động React
  - Render `App` vào DOM

- `App.jsx`
  - App chính
  - Hiện tại chỉ render `HomePage`

### `frontend/src/pages/`

- `HomePage.jsx`
  - File quan trọng nhất bên frontend
  - Chứa luồng giao diện chính:
    - nhập text
    - chọn file
    - chọn `LLM Mode`
    - bấm `Extract`
    - bấm `Calculate`
    - gọi API
    - xử lý loading/success/error
    - hiển thị kết quả extraction và UCP
  - Nếu muốn đổi hành vi UI chính thì xem file này trước

### `frontend/src/api/`

- `client.js`
  - Nơi gom toàn bộ lệnh gọi API backend
  - Chứa:
    - `checkHealth()`
    - `extractData()`
    - `calculateUCP()`
    - `analyzeAndCalculate()`
  - Nếu frontend gọi sai API hoặc xử lý lỗi chưa đẹp thì xem file này

### `frontend/src/utils/`

- `requestHelpers.js`
  - Hàm hỗ trợ tạo payload cho frontend
  - Ví dụ:
    - tạo payload gửi sang `/ucp/calculate`
    - tạo chữ ký input để biết extraction cũ còn hợp lệ không

### `frontend/src/components/`

- `ActorsTable.jsx`
  - Hiển thị bảng Actor

- `UseCasesTable.jsx`
  - Hiển thị bảng Use Case

- `ResultCards.jsx`
  - Hiển thị các thẻ kết quả:
    - UAW
    - UUCW
    - UCP
    - Effort
    - Schedule

- `ChartPanel.jsx`
  - Hiển thị biểu đồ Chart.js
  - So sánh số lượng Actor và Use Case theo mức complexity

### `frontend/src/styles/`

- `index.css`
  - Toàn bộ style chính của giao diện

## 4. Giải thích nhanh về LLM Mode

`LLM Mode` hiện có 2 chế độ:

- `Mock Mode`
  - Không gọi AI thật
  - Dùng rule-based extraction nội bộ
  - Phù hợp để demo ổn định, không phụ thuộc API key hay Internet
  - Dùng tốt khi cần test, kiểm thử, trình bày trên lớp

- `Placeholder API Mode`
  - Chưa gọi AI thật, nhưng mô phỏng đúng chỗ mà sau này sẽ nối LLM API
  - Backend vẫn build prompt extraction
  - Giúp project giữ kiến trúc rõ ràng:
    - hôm nay chạy demo ổn định
    - ngày mai có thể thay bằng LLM thật mà không phải sửa toàn bộ hệ thống

## 5. Khi cần tìm file nào?

- Muốn giải thích API chạy ở đâu:
  - `backend/app/api/routes/analysis.py`

- Muốn giải thích vì sao actor/use case bị đổi tên hoặc đổi complexity:
  - `backend/app/utils/normalization.py`

- Muốn giải thích prompt cho LLM:
  - `backend/app/services/prompt_templates.py`

- Muốn giải thích LLM Mode:
  - `backend/app/services/llm_extractor.py`
  - `frontend/src/pages/HomePage.jsx`

- Muốn giải thích công thức UCP:
  - `backend/app/services/ucp_calculator.py`

- Muốn giải thích Effort và Schedule:
  - `backend/app/services/effort_estimation_service.py`
  - `backend/app/services/schedule_estimation_service.py`

- Muốn giải thích frontend gọi backend như thế nào:
  - `frontend/src/api/client.js`

- Muốn giải thích nút Extract / Calculate làm gì:
  - `frontend/src/pages/HomePage.jsx`

- Muốn chứng minh hệ thống đã có test:
  - `backend/tests/test_api.py`
  - `backend/tests/test_llm_extractor.py`
  - `backend/tests/test_ucp_calculator.py`
