# Thuyết Minh Code AI Tool for Automatic UCPE

Tài liệu này giải thích luồng chạy của hệ thống theo kiểu dễ trình bày:

1. Người dùng nhập dữ liệu ở đâu
2. Frontend xử lý gì
3. Backend nhận gì
4. Extraction chạy ra sao
5. Normalization làm gì
6. UCP được tính như thế nào
7. Kết quả trả về giao diện ra sao

Mục tiêu là để khi bảo vệ đồ án hoặc bị hỏi về source code, bạn có thể kể lại luồng xử lý một cách logic, rõ ràng và bám sát file thật trong project.

---

## 1. Mục tiêu của hệ thống

Hệ thống này được xây dựng để hỗ trợ **Use Case Point Estimation** từ **Requirements Text** hoặc **Use Case Description** ở dạng văn bản tự nhiên.

Đầu vào của hệ thống là:
- đoạn mô tả yêu cầu
- đoạn use case mô tả ngắn
- hoặc nội dung text lấy từ file upload

Đầu ra của hệ thống là:
- danh sách `Actor`
- danh sách `Use Case`
- `UAW`
- `UUCW`
- `UUCP`
- `UCP`
- `Effort`
- `Schedule`

Điểm quan trọng là hệ thống **không yêu cầu người dùng phải nhập theo mẫu Use Case Specification đầy đủ**, mà chỉ cần đưa văn bản mô tả tự nhiên.

---

## 2. Luồng tổng quát của hệ thống

Luồng chạy tổng quát có thể mô tả ngắn như sau:

1. Người dùng nhập text ở frontend.
2. Frontend gửi dữ liệu sang backend.
3. Backend đọc text và trích xuất actor/use case.
4. Backend chuẩn hóa dữ liệu extraction.
5. Backend dùng dữ liệu đã chuẩn hóa để tính UCP.
6. Backend trả kết quả về frontend.
7. Frontend hiển thị bảng, thẻ kết quả và biểu đồ.

Nếu muốn nói ngắn gọn khi thuyết trình, bạn có thể dùng câu sau:

> Hệ thống của em gồm 3 lớp chính: extraction, normalization và UCP calculation. Frontend chỉ có nhiệm vụ nhập liệu và hiển thị; còn backend sẽ chịu trách nhiệm trích xuất, làm sạch dữ liệu và tính toán kết quả cuối cùng.

---

## 3. Bước 1: Người dùng nhập dữ liệu ở frontend

### File liên quan

- `frontend/src/pages/HomePage.jsx`

### Vai trò của file này

Đây là trang chính của hệ thống. Người dùng thao tác chủ yếu ở file này.

Tại đây có các ô nhập:
- `Requirements Text / Use Case Description`
- `Plain Text Input File`
- `LLM Mode`
- `TCF`
- `ECF`
- `Productivity Factor`
- `Team Size`

Ngoài ra còn có 2 nút:
- `Trích Xuất`
- `Tính Toán`

### Ý nghĩa thao tác của người dùng

#### Khi bấm `Trích Xuất`

Frontend sẽ gọi API:
- `POST /extract`

Mục tiêu:
- chỉ lấy `Actor`
- chỉ lấy `Use Case`
- chưa tính UCP

#### Khi bấm `Tính Toán`

Frontend có 2 trường hợp:

- Nếu trước đó đã extract và dữ liệu đầu vào chưa đổi:
  - frontend gọi `POST /ucp/calculate`
  - nghĩa là dùng dữ liệu extraction đang có để tính UCP luôn

- Nếu người dùng chưa extract, hoặc đã đổi text, đổi file, đổi mode:
  - frontend gọi `POST /analyze-and-calculate`
  - nghĩa là backend sẽ vừa extract vừa tính trong một bước

### Vì sao frontend làm như vậy

Lý do là để:
- giảm gọi API lặp lại không cần thiết
- giữ giao diện phản hồi nhanh hơn
- và tách rõ luồng `extract` với luồng `calculate`

### Các hàm chính ở frontend

Trong `HomePage.jsx`, có các hàm:

- `handleExtract()`
  - gọi API trích xuất
- `handleCalculate()`
  - gọi API tính toán
- `handleInputChange()`
  - cập nhật state khi người dùng nhập dữ liệu

Ngoài ra frontend còn dùng:
- `buildInputSignature()`
  - để biết dữ liệu nhập hiện tại có giống dữ liệu đã extract trước đó không
- `buildUcpPayload()`
  - để tạo payload gửi lên backend đúng định dạng

Các hàm này nằm ở:
- `frontend/src/utils/requestHelpers.js`

---

## 4. Bước 2: Frontend gọi API backend

### File liên quan

- `frontend/src/api/client.js`

### Vai trò

File này gom tất cả lệnh gọi API vào một nơi.

Các hàm chính:
- `checkHealth()`
- `extractData(text, options)`
- `calculateUCP(payload)`
- `analyzeAndCalculate(text, options)`

### Ý nghĩa

Thay vì viết `fetch()` rải rác khắp giao diện, project gom lại vào `client.js` để:
- code dễ đọc hơn
- dễ sửa địa chỉ API hơn
- dễ xử lý lỗi hơn

### Xử lý lỗi

`client.js` có:
- `ApiError`
- `formatErrorMessage()`

Mục đích là:
- khi backend trả lỗi validation
- hoặc backend không chạy
- frontend sẽ hiện lỗi dễ hiểu hơn cho người dùng

Ví dụ:
- backend chưa chạy thì hiện thông báo không thể kết nối
- backend báo sai dữ liệu thì hiện chi tiết field bị lỗi

---

## 5. Bước 3: Backend nhận request

### File liên quan

- `backend/app/main.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/analysis.py`
- `backend/app/api/routes/health.py`

### Vai trò từng file

#### `main.py`

Đây là điểm khởi động của FastAPI.

Nó làm 3 việc chính:
- tạo ứng dụng FastAPI
- bật CORS để frontend React gọi được backend
- nạp router tổng

#### `router.py`

File này gom các nhóm route:
- `health`
- `analysis`

#### `health.py`

Chứa API:
- `GET /health`

Frontend dùng API này để kiểm tra backend có đang hoạt động hay không.

#### `analysis.py`

Đây là file route quan trọng nhất.

Nó chứa 3 endpoint chính:
- `POST /extract`
- `POST /ucp/calculate`
- `POST /analyze-and-calculate`

---

## 6. Bước 4: Backend đọc input text và file upload

### File liên quan

- `backend/app/api/routes/analysis.py`
- `backend/app/utils/file_reader.py`
- `backend/app/utils/parser.py`

### Luồng hoạt động

Khi request đi vào route `extract` hoặc `analyze-and-calculate`, backend sẽ:

1. đọc text từ form
2. đọc file upload nếu có
3. biến nội dung file thành text
4. gộp text nhập tay và text từ file thành một chuỗi chung

### `file_reader.py` làm gì

File này có hàm:
- `read_uploaded_text(uploaded_file)`

Hàm này:
- đọc bytes của file
- thử decode sang UTF-8
- nếu lỗi thì fallback sang latin-1

Mục tiêu là để prototype có thể đọc được file text đơn giản mà không làm hệ thống quá phức tạp.

### `parser.py` làm gì

File này có các helper cơ bản:
- `combine_text_sources()`
  - ghép text nhập tay và text từ file
- `split_sentences()`
  - tách đoạn văn thành câu
- `normalize_name()`
  - chuẩn hóa khoảng trắng

---

## 7. Bước 5: Backend chọn LLM Mode để extraction

### File liên quan

- `backend/app/services/llm_extractor.py`
- `backend/app/services/prompt_templates.py`

### Đây là nơi `LLM Mode` thực sự có tác dụng

Trong `llm_extractor.py`, hàm chính là:
- `extract_requirements(request_model)`

Hàm này sẽ gọi:
- `_generate_extraction_json(text, mode)`

Tại đây backend sẽ kiểm tra giá trị `llm_mode`.

### Nếu là `mock`

Backend chạy:
- `_build_mock_extraction_json(text)`

Nghĩa là:
- dùng extractor nội bộ theo rule
- không gọi AI thật

### Nếu là `placeholder`

Backend chạy:
- `_call_placeholder_llm_api(text)`

Hiện tại hàm này:
- build prompt qua `build_extraction_prompt()`
- nhưng vẫn trả về dữ liệu từ extractor nội bộ

Điều này có ý nghĩa rất quan trọng về mặt kiến trúc:
- hệ thống đã có sẵn vị trí để nối LLM thật
- nhưng ở phiên bản demo vẫn giữ kết quả ổn định

### Khi trình bày, bạn có thể nói

> Trong project hiện tại, LLM Mode dùng để chọn nhánh extraction. Mock Mode phục vụ demo local ổn định. Placeholder API Mode mô phỏng chỗ tích hợp LLM thật, giúp hệ thống dễ nâng cấp trong tương lai mà không cần đổi kiến trúc.

---

## 8. Bước 6: Extraction thô actor và use case

### File liên quan

- `backend/app/services/llm_extractor.py`

### Ý tưởng của extraction thô

Project chia extraction thành 2 lớp:

1. lớp trích xuất thô
2. lớp normalization làm sạch lại

Lý do chia như vậy:
- extraction ban đầu có thể chưa hoàn hảo
- nhưng normalization sẽ sửa lại để dữ liệu dùng được cho UCP

### Trích xuất actor

Hàm:
- `_extract_raw_actors(text)`

Nó dùng regex để bắt các mẫu câu như:
- `The Customer can ...`
- `The Administrator can ...`
- `Payment Gateway ...`

Kết quả lúc này mới chỉ là candidate, chưa chắc đúng hoàn toàn.

### Trích xuất use case

Hàm:
- `_extract_raw_use_cases(text)`

Luồng làm việc:

1. tách đoạn văn thành từng câu
2. kiểm tra câu có dấu hiệu hành động hay không
3. cắt bỏ phần chủ ngữ
4. tách một câu thành nhiều hành động nhỏ
5. tạo danh sách use case thô

Ví dụ:

Nếu câu là:

`The Customer can browse products, search products, and place order.`

thì extractor thô sẽ tách ra thành các đoạn:
- `browse products`
- `search products`
- `place order`

Sau đó gán complexity sơ bộ ban đầu.

### Vì sao chỉ gán complexity sơ bộ

Vì complexity cuối cùng sẽ do normalization classifier xử lý lại.

Điều này giúp:
- giữ layer extraction đơn giản
- dồn logic quan trọng về một chỗ chung là normalization

---

## 9. Bước 7: Parse JSON extraction

### File liên quan

- `backend/app/utils/llm_json_parser.py`

### Vai trò

Sau khi extractor trả ra JSON, backend không dùng ngay mà phải parse và validate lại.

Hàm chính:
- `parse_llm_extraction_json(raw_json)`

### Công việc của parser

1. đọc JSON string
2. kiểm tra đúng schema hay không
3. kiểm tra complexity có phải:
   - `simple`
   - `average`
   - `complex`
4. bỏ các phần tử trùng tên

### Vì sao bước này cần thiết

Nếu bỏ qua parser:
- JSON lỗi có thể làm backend crash
- complexity sai có thể làm công thức UCP bị sai
- dữ liệu không nhất quán sẽ rất khó debug

---

## 10. Bước 8: Normalization là lớp quan trọng nhất

### File liên quan

- `backend/app/utils/normalization.py`
- `backend/app/services/mapping_config.py`

Đây là phần quan trọng nhất của toàn bộ backend extraction pipeline.

Nếu bị hỏi:
- “Vì sao actor này lại bị loại?”
- “Vì sao use case này lại đổi tên?”
- “Vì sao complexity này thành complex?”

thì gần như câu trả lời sẽ nằm ở `normalization.py` hoặc `mapping_config.py`.

### Mục tiêu của normalization

Normalization giúp:
- làm sạch dữ liệu extraction
- loại bỏ kết quả sai
- chuẩn hóa tên
- deduplicate
- phân loại lại complexity

### 10.1. Chuẩn hóa actor

Hàm:
- `normalize_actors()`
- `_normalize_actor_item()`

Các rule chính:

- bỏ `System` khỏi actor
- human actor luôn là `complex`
  - ví dụ: Customer, Student, Instructor, Guest, Doctor
- external system luôn là `simple`
  - ví dụ: Payment Gateway, Email Service, API
- nếu actor trùng nhau thì chỉ giữ một
- nếu có actor chung chung và actor cụ thể hơn:
  - `Manager`
  - `Hotel Manager`
  - thì giữ `Hotel Manager`

### 10.2. Chuẩn hóa use case

Hàm:
- `normalize_use_cases()`
- `_normalize_use_case_item()`

Các rule chính:

- đưa tên về dạng `Verb + Noun`
- giữ domain noun
  - `Search Books` vẫn là `Search Books`
  - không đổi thành `Search Products`
- bỏ sentence fragment
- bỏ internal step
  - ví dụ:
    - `Send Confirmation`
    - `Send Reminder`
    - `Notify User`
    - `Update Status`
- merge sub-action thành use case cha
  - ví dụ:
    - `update room availability`
    - `delete room information`
    - có thể được gom về `Manage Room Information`

### 10.3. Phân loại complexity

Hàm:
- `_classify_use_case_complexity()`

Rule chính:

- `simple`
  - login
  - search
  - view
  - browse
  - check

- `average`
  - register
  - create
  - submit
  - confirm
  - approve
  - return
  - payment

- `complex`
  - book
  - reserve
  - borrow
  - place order
  - enroll
  - schedule
  - manage

Thứ tự ưu tiên:
- complex override average
- average override simple

Ngoài ra còn có rule tránh phân loại sai do domain noun.

Ví dụ:
- `Book Rooms`
  - chữ `Book` ở đầu là động từ
  - nên là `complex`

- `View Book Details`
  - chữ `Book` ở đây là danh từ chỉ domain object
  - nên không được hiểu nhầm là hành động `book`

Đây là lý do project có hàm:
- `_contains_action_keyword()`

### Ý nghĩa học thuật của normalization

Nếu không có normalization:
- extraction rất dễ bị sai
- UAW sai
- UUCW sai
- UCP sai toàn bộ

Nói cách khác:

> Extraction cho dữ liệu thô, nhưng normalization mới là lớp biến dữ liệu thô thành dữ liệu đủ sạch để dùng cho UCP.

---

## 11. Bước 9: Dữ liệu được đưa vào bộ tính UCP

### File liên quan

- `backend/app/api/routes/analysis.py`
- `backend/app/models/request_models.py`
- `backend/app/services/ucp_calculator.py`

### Luồng chuyển dữ liệu

Sau khi extraction được normalize xong, backend tạo một object `UCPRequest`.

Model này chứa:
- `actors`
- `use_cases`
- `tcf`
- `ecf`
- `productivity_factor`

Trước khi đi vào bộ tính, backend đảm bảo:
- có ít nhất 1 actor
- có ít nhất 1 use case
- các hệ số lớn hơn 0

### Vì sao cần model riêng cho UCP

Để tách biệt:
- dữ liệu API
- và dữ liệu nội bộ của công thức

Nhờ vậy phần tính toán:
- đơn giản hơn
- dễ test hơn
- dễ giải thích hơn

---

## 12. Bước 10: Tính UCP

### File liên quan

- `backend/app/services/ucp_calculator.py`

Đây là file chứa công thức lõi.

### 12.1. Tính trọng số actor

Hàm:
- `calculate_actor_weight(complexity)`

Rule:
- `simple = 1`
- `average = 2`
- `complex = 3`

### 12.2. Tính trọng số use case

Hàm:
- `calculate_use_case_weight(complexity)`

Rule:
- `simple = 5`
- `average = 10`
- `complex = 15`

### 12.3. Tính UAW

Hàm:
- `calculate_uaw(actors)`

Công thức:

`UAW = tổng trọng số của tất cả actor`

### 12.4. Tính UUCW

Hàm:
- `calculate_uucw(use_cases)`

Công thức:

`UUCW = tổng trọng số của tất cả use case`

### 12.5. Tính UUCP

Hàm:
- `calculate_uucp(uaw, uucw)`

Công thức:

`UUCP = UAW + UUCW`

### 12.6. Tính UCP

Hàm:
- `calculate_ucp(uucp, tcf, ecf)`

Công thức:

`UCP = UUCP * TCF * ECF`

### 12.7. Tính Effort

Hàm:
- `calculate_effort_estimation(ucp, productivity_factor)`

Công thức:

`Effort = UCP * productivity_factor`

### 12.8. Hàm tổng hợp

Hàm:
- `calculate_ucp_metrics(request_data)`

Hàm này gọi toàn bộ các bước trên theo đúng thứ tự và trả ra:
- `uaw`
- `uucw`
- `uucp`
- `ucp`
- `effort_estimation`

---

## 13. Bước 11: Tính Effort và Schedule

### File liên quan

- `backend/app/services/effort_estimation_service.py`
- `backend/app/services/schedule_estimation_service.py`

### `effort_estimation_service.py`

Hàm:
- `estimate_effort(ucp, productivity_factor)`

Kết quả trả ra:
- `hours`
- `person_days`
- `productivity_factor`

### `schedule_estimation_service.py`

Hàm:
- `estimate_schedule(hours, team_size)`

Công thức đang dùng:

`months = effort_hours / (team_size * 160)`

Tức là:
- 1 người làm 160 giờ mỗi tháng
- nếu nhóm có nhiều người thì thời gian giảm xuống

Ngoài ra còn tính:
- `recommended_team_size`
- `sprint_count`

---

## 14. Bước 12: Backend trả response về frontend

### Nếu gọi `/extract`

Backend trả:
- `actors`
- `use_cases`
- `notes`

### Nếu gọi `/ucp/calculate`

Backend trả:
- `ucp`
- `effort`
- `schedule`

### Nếu gọi `/analyze-and-calculate`

Backend trả đầy đủ:
- `extraction`
- `ucp`
- `effort`
- `schedule`

### File model response

- `backend/app/models/responses.py`
- `backend/app/models/response_models.py`

---

## 15. Bước 13: Frontend hiển thị kết quả

### File liên quan

- `frontend/src/pages/HomePage.jsx`
- `frontend/src/components/ActorsTable.jsx`
- `frontend/src/components/UseCasesTable.jsx`
- `frontend/src/components/ResultCards.jsx`
- `frontend/src/components/ChartPanel.jsx`

### Vai trò từng component

#### `ActorsTable.jsx`

Hiển thị bảng Actor:
- tên actor
- complexity

#### `UseCasesTable.jsx`

Hiển thị bảng Use Case:
- tên use case
- complexity

#### `ResultCards.jsx`

Hiển thị thẻ kết quả:
- UAW
- UUCW
- UCP
- Effort
- Schedule

#### `ChartPanel.jsx`

Hiển thị biểu đồ cột bằng Chart.js:
- số lượng Actor theo complexity
- số lượng Use Case theo complexity

### Ý nghĩa

Nhờ tách component như vậy, giao diện:
- dễ đọc
- dễ sửa
- và khi cần demo, có thể chỉ thẳng từng khu vực chức năng

---

## 16. Vai trò của test trong project

### File liên quan

- `backend/tests/test_api.py`
- `backend/tests/test_llm_extractor.py`
- `backend/tests/test_ucp_calculator.py`

### Ý nghĩa từng file

#### `test_api.py`

Chứng minh API backend hoạt động đúng:
- health
- extract
- calculate
- analyze-and-calculate

#### `test_llm_extractor.py`

Chứng minh extraction + normalization chạy đúng:
- actor được nhận diện đúng
- use case không bị fragment
- internal step bị loại bỏ
- complexity phân loại đúng

#### `test_ucp_calculator.py`

Chứng minh công thức UCP đúng:
- actor weight
- use case weight
- UAW
- UUCW
- UUCP
- UCP
- effort
- schedule

### Nếu bị hỏi “làm sao chứng minh hệ thống đúng?”

Bạn có thể trả lời:

> Em dùng test ở 3 tầng. Một là test công thức UCP, hai là test extraction-normalization, ba là test API end-to-end. Nhờ vậy em có thể kiểm tra từ logic nhỏ nhất đến toàn bộ luồng backend.

---

## 17. Tóm tắt ngắn gọn để thuyết trình

Nếu bạn cần một bản cực ngắn để nói trong 1 phút, có thể dùng như sau:

> Hệ thống của em bắt đầu từ frontend React, nơi người dùng nhập Requirements Text hoặc tải file text lên. Sau đó frontend gọi backend FastAPI qua các API như `/extract` hoặc `/analyze-and-calculate`. Ở backend, dữ liệu đầu vào được đọc và gộp lại, rồi đi vào extraction service để lấy actor và use case. Kết quả extraction chưa dùng ngay mà phải qua lớp normalization để loại `System`, gộp trùng, chuẩn hóa tên use case và phân loại lại complexity. Sau khi có dữ liệu sạch, hệ thống mới đưa vào module `ucp_calculator.py` để tính UAW, UUCW, UUCP và UCP. Từ UCP, backend tiếp tục tính Effort và Schedule, rồi trả toàn bộ kết quả về frontend để hiển thị bằng bảng, card và biểu đồ.

---

## 18. Nếu bị hỏi “chức năng này nằm ở đâu?”

Bạn có thể trả lời nhanh theo bảng sau:

- Nhập liệu và bấm nút:
  - `frontend/src/pages/HomePage.jsx`

- Gọi API:
  - `frontend/src/api/client.js`

- Route backend:
  - `backend/app/api/routes/analysis.py`

- Trích xuất actor/use case:
  - `backend/app/services/llm_extractor.py`

- Prompt cho LLM:
  - `backend/app/services/prompt_templates.py`

- Rule normalize và complexity:
  - `backend/app/utils/normalization.py`
  - `backend/app/services/mapping_config.py`

- Công thức UCP:
  - `backend/app/services/ucp_calculator.py`

- Effort:
  - `backend/app/services/effort_estimation_service.py`

- Schedule:
  - `backend/app/services/schedule_estimation_service.py`

- Test:
  - `backend/tests/`

---

## 19. Kết luận

Điểm mạnh của project này là kiến trúc được tách thành các lớp rõ ràng:

- **Frontend**
  - chỉ nhập liệu và hiển thị

- **Extraction layer**
  - lấy actor/use case từ văn bản tự nhiên

- **Normalization layer**
  - sửa dữ liệu cho đúng rule UCP

- **Calculation layer**
  - tính UCP, Effort, Schedule

Cách tách lớp này giúp project:
- dễ đọc
- dễ test
- dễ giải thích trong báo cáo
- và dễ mở rộng nếu sau này nối LLM thật
