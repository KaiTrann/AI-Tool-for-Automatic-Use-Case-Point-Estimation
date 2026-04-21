# THUYET_MINH_CODE_VI

Tài liệu này giải thích luồng chạy của hệ thống theo kiểu dễ dùng để thuyết trình:
- người dùng nhập gì
- frontend gửi gì
- backend xử lý ra sao
- actor và use case được trích xuất như thế nào
- vì sao ra được `UAW`, `UUCW`, `UCP`, `Effort`, `Schedule`

## 1. Mục tiêu của hệ thống

Hệ thống được xây để hỗ trợ `Use Case Point Estimation`.

Đầu vào có thể là:
- `Requirements Text`
- `Use Case Description`
- file `Use Case Document / SRS`
- file IEEE 830-1998 style SRS như HR/Payroll Dashboard

Đầu ra gồm:
- danh sách `Actor`
- danh sách `Use Case`
- `UAW`
- `UUCW`
- `UUCP`
- `UCP`
- `Effort`
- `Schedule`

Ý tưởng chính của project:
- không tính UCP trực tiếp từ văn bản thô
- phải đi qua bước trích xuất và chuẩn hóa trước

Vì vậy hệ thống được chia thành 3 lớp:

1. `Extraction layer`
2. `Normalization layer`
3. `Calculation layer`

## 2. Luồng chạy tổng quát

Luồng đầy đủ từ lúc người dùng nhập dữ liệu đến lúc ra kết quả như sau:

1. Người dùng nhập text hoặc upload file trên frontend.
2. Frontend gửi request sang backend.
3. Backend đọc text và nội dung file upload.
4. Backend kiểm tra input là:
   - free-text
   - hay Use Case Document / SRS có cấu trúc
5. Backend trích xuất actor và use case.
6. Dữ liệu trích xuất đi qua bước normalization.
7. Dữ liệu sạch được đưa sang bộ tính UCP.
8. Backend tính `Effort` và `Schedule`.
9. Kết quả được trả về frontend để hiển thị.

Nếu cần nói ngắn gọn khi bảo vệ:

> Hệ thống của em có 3 lớp chính: trích xuất dữ liệu, chuẩn hóa dữ liệu, rồi mới tính UCP. Điều này giúp giảm lỗi khi đầu vào là text tự do hoặc tài liệu SRS/use case document.

## 3. Bước 1: Người dùng nhập dữ liệu trên frontend

### File chính

- `frontend/src/pages/HomePage.jsx`

### Vai trò

Đây là trang chính của project.

Người dùng có thể:
- nhập text trực tiếp
- upload file `.txt`, `.docx`, `.doc`
- chọn `LLM Mode`
- nhập `TCF`, `ECF`, `Productivity Factor`, `Team Size`
- bấm `Extract`
- bấm `Calculate`

### Hai cách dùng chính

#### Cách 1: chỉ trích xuất

Người dùng bấm `Extract` để lấy:
- danh sách actor
- danh sách use case

Frontend sẽ gọi:

```text
POST /extract
```

#### Cách 2: trích xuất và tính toán

Người dùng bấm `Calculate`.

Khi đó frontend có thể:
- gọi `/ucp/calculate` nếu đã có extraction hợp lệ
- hoặc gọi `/analyze-and-calculate` nếu cần extract lại

## 4. Bước 2: Frontend gọi API

### File chính

- `frontend/src/api/client.js`

### Vai trò

File này gom các hàm gọi backend:
- `checkHealth()`
- `extractData()`
- `calculateUCP()`
- `analyzeAndCalculate()`

Lợi ích của việc gom API vào 1 file:
- dễ sửa địa chỉ backend
- dễ quản lý lỗi
- dễ giải thích khi bị hỏi frontend giao tiếp backend ở đâu

## 5. Bước 3: Backend nhận request

### File chính

- `backend/app/main.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/analysis.py`

### Vai trò

#### `main.py`

- tạo app FastAPI
- bật CORS
- include router

#### `router.py`

- gom route health và analysis

#### `analysis.py`

Đây là route quan trọng nhất, chứa:
- `POST /extract`
- `POST /ucp/calculate`
- `POST /analyze-and-calculate`

File này chịu trách nhiệm:
- nhận text/file từ frontend
- gọi extraction service
- chuẩn hóa dữ liệu trước khi tính
- gọi UCP calculator
- trả kết quả về frontend

## 6. Bước 4: Backend đọc text và file upload

### File chính

- `backend/app/api/routes/analysis.py`
- `backend/app/utils/file_reader.py`
- `backend/app/utils/parser.py`

### Luồng xử lý

1. route lấy text từ form
2. nếu có file upload thì gọi `file_reader.py`
3. file được đổi thành text
4. text nhập tay và text từ file được ghép lại

### `file_reader.py` làm gì

File này đọc nội dung upload và chuyển về text.

Hiện hỗ trợ:
- `.txt`
- `.md`
- `.docx`
- `.doc` theo kiểu best-effort

Điểm quan trọng:
- project hiện đã đọc được file `.docx` để demo
- không còn chỉ xử lý text đơn giản như giai đoạn đầu nữa

### `parser.py` làm gì

File này chứa các helper như:
- ghép nhiều nguồn text
- chuẩn hóa khoảng trắng
- tách câu

## 7. Bước 5: LLM Mode có tác dụng gì

### File chính

- `backend/app/services/llm_extractor.py`
- `backend/app/services/prompt_templates.py`

`LLM Mode` là dropdown để chọn cách backend xử lý extraction.

### `Mock Mode`

Công dụng cụ thể:
- dùng extractor rule-based nội bộ
- không gọi AI thật
- cho kết quả ổn định khi demo
- không cần API key
- không cần internet

### `Placeholder API Mode`

Công dụng cụ thể:
- giữ chỗ cho hướng tích hợp LLM API thật
- backend vẫn build prompt để mô phỏng kiến trúc AI
- hiện vẫn fallback về extractor nội bộ để tránh lỗi demo

Nói ngắn gọn:
- `Mock Mode` để demo ổn định
- `Placeholder API Mode` để chứng minh hệ thống có thể nâng cấp sang AI thật

## 8. Bước 6: Backend xác định loại input

### File chính

- `backend/app/services/llm_extractor.py`
- `backend/app/utils/use_case_document_parser.py`

Backend hiện có 2 đường xử lý:

### Đường 1: Free-text

Dùng khi input là:
- requirement paragraph
- mô tả use case ngắn
- text không theo template chuẩn

### Đường 2: Structured document

Dùng khi input có dấu hiệu là tài liệu Use Case / SRS, ví dụ có các field:
- `Use Case ID`
- `Use Case Name`
- `Actors`
- `Description`
- `Main Flow`
- `Alternative Flow`
- `Pre-conditions`
- `Post-conditions`

Nếu backend nhận ra đây là tài liệu có cấu trúc thì nó sẽ ưu tiên parse theo block use case, thay vì đoán use case từ câu văn.

Điều này quan trọng vì:
- giảm lỗi sentence fragment
- lấy được actor sạch hơn
- tính complexity chính xác hơn bằng transaction count
- hỗ trợ được template IEEE/HR có `5.2 List of Use Case` và `5.4 Use Case Specification`

## 9. Bước 7: Parser tài liệu SRS / Use Case Document

### File chính

- `backend/app/utils/use_case_document_parser.py`
- `backend/app/utils/actor_normalizer.py`
- `backend/app/utils/use_case_extractor.py`

### Mục tiêu của parser

Parser được sửa để:
- không lấy mục lục làm use case
- không lấy metadata như `Created by`, `Date updated`
- đọc được cả `List of Use Case` và `Use Case Specification`
- không phụ thuộc vào số section cố định như `2.4.5` hoặc `5.4`
- tách đúng từng use case block

### Cách parser hoạt động

1. tìm section `List of Use Case` nếu có
2. đọc danh sách use case cấp cao từ bảng list
3. tìm section `Use Case Specification`
4. xác định từng block `UC.01`, `UC 02`, ...
5. trong từng block chỉ đọc các field quan trọng
6. merge dữ liệu list và block chi tiết bằng `Use Case ID`
7. lấy `Use case name` làm nguồn chính cho tên use case
8. lấy `Actors` để chuẩn hóa actor
9. tách `Main Flow`, `Alternative Flow`, `Exception Flow` thành danh sách bước

Với file IEEE/HR thật:
- `5.2 List of Use Case` có thể chứa nhiều use case hơn phần đặc tả chi tiết
- nếu một use case chỉ có trong list, hệ thống vẫn giữ use case đó
- nếu có block chi tiết, hệ thống ưu tiên transaction count từ `Main Flow`

### `actor_normalizer.py` làm gì

File này làm sạch chuỗi actor như:

```text
Users of the system, including: Librarian, Stocker, Reading Management Staff
```

thành:
- `Librarian`
- `Stocker`
- `Reading Management Staff`

### `use_case_extractor.py` làm gì

File này đảm bảo tên use case được lấy đúng ưu tiên:

1. `Use case name`
2. nếu thiếu thì dùng header `UC 01: Login`

Nhờ vậy backend không còn lấy nhầm:
- dòng mục lục
- metadata
- đoạn văn dài

## 10. Bước 8: Extraction actor và use case

### File chính

- `backend/app/services/llm_extractor.py`

### Nếu là free-text

Backend sẽ:
- tách câu
- tìm actor candidate bằng pattern
- tìm action candidate trong câu
- tạo actor/use case thô

Ví dụ:

```text
The Customer can browse products, search products, and place order.
```

sẽ được tách thành:
- `Browse Products`
- `Search Products`
- `Place Order`

### Nếu là tài liệu có cấu trúc

Backend sẽ:
- parse từng use case document
- lấy actor từ field actor
- lấy use case từ field name
- chuẩn hóa rồi phân loại theo chuẩn UCP

Điểm quan trọng:
- dữ liệu có cấu trúc luôn được ưu tiên hơn heuristic keyword

## 11. Bước 9: Normalization là lớp quan trọng nhất

### File chính

- `backend/app/utils/normalization.py`

Đây là lớp làm sạch dữ liệu trước khi tính UCP.

Nếu extraction bị sai tên, bị trùng, hoặc có use case nội bộ thừa thì phần lớn lỗi nằm ở đây.

### 11.1. Normalization actor

Hệ thống sẽ:
- bỏ actor `System`
- bỏ actor trùng
- chuẩn hóa tên actor
- giữ actor cụ thể hơn nếu có 2 actor chồng lấp

Ví dụ:
- `Manager`
- `Hotel Manager`

thì giữ:
- `Hotel Manager`

### 11.2. Actor classification theo chuẩn UCP

### File chính

- `backend/app/services/actor_classifier.py`

Rule đang dùng:
- `simple`: external system có API rõ
- `average`: giao tiếp qua file / database / protocol / text
- `complex`: human actor thao tác qua GUI

Ví dụ:
- `Customer` -> `complex`
- `Administrator` -> `complex`
- `Payment Gateway` -> `simple`

### 11.3. Normalization use case

Hệ thống sẽ:
- đưa tên về dạng `Verb + Noun`
- bỏ trùng
- bỏ sentence fragment
- giữ domain noun đúng
- loại internal step

Ví dụ:
- `The System Allows A Customer To` -> bị loại
- `Search Rooms` -> giữ nguyên domain noun `Rooms`
- `Search Products` -> giữ nguyên domain noun `Products`

### 11.4. Loại internal step

Các mục như sau sẽ không được tính là use case:
- `Send Confirmation`
- `Send Reminder`
- `Notify User`
- `Log Activity`
- `Update Status`

Lý do:
- đây là hành vi nội bộ của hệ thống
- không phải business goal do actor theo đuổi

### 11.5. Use case complexity theo chuẩn UCP

### File chính

- `backend/app/services/use_case_classifier.py`

Chuẩn đang áp dụng:
- `<= 3 transactions` -> `simple`
- `4–7 transactions` -> `average`
- `> 7 transactions` -> `complex`

Điểm quan trọng:
- với tài liệu có cấu trúc, complexity được ưu tiên tính bằng số transaction
- rule keyword chỉ là fallback khi input không đủ cấu trúc

## 12. Bước 10: Dữ liệu sạch được chuyển sang bộ tính UCP

### File chính

- `backend/app/api/routes/analysis.py`
- `backend/app/services/ucp_calculator.py`

Trước khi tính UCP, route sẽ normalize lại một lần nữa để chắc chắn:
- không còn actor/use case trùng
- complexity đúng chuẩn
- payload sạch cho calculation layer

## 13. Bước 11: Công thức tính UCP

### File chính

- `backend/app/services/ucp_calculator.py`

### Chuẩn đang dùng

#### Actor weight

- `simple = 1`
- `average = 2`
- `complex = 3`

#### Use case weight

- `simple = 5`
- `average = 10`
- `complex = 15`

#### Công thức

- `UAW = tổng trọng số actor`
- `UUCW = tổng trọng số use case`
- `UUCP = UAW + UUCW`
- `UCP = UUCP * TCF * ECF`

## 14. Bước 12: Tính Effort và Schedule

### File chính

- `backend/app/services/effort_estimation_service.py`
- `backend/app/services/schedule_estimation_service.py`

### Effort

```text
Effort = UCP * productivity_factor
```

### Schedule

```text
Schedule = effort_hours / (team_size * 160)
```

Ý nghĩa:
- mặc định 1 người làm 160 giờ mỗi tháng
- team lớn hơn thì số tháng dự kiến giảm xuống

## 15. Bước 13: Backend trả kết quả về frontend

### `POST /extract`

Trả về:
- `actors`
- `use_cases`
- `notes`

### `POST /ucp/calculate`

Trả về:
- `ucp`
- `effort`
- `schedule`

### `POST /analyze-and-calculate`

Trả về đầy đủ:
- `extraction`
- `ucp`
- `effort`
- `schedule`

## 16. Bước 14: Frontend hiển thị kết quả

### File chính

- `frontend/src/components/ActorsTable.jsx`
- `frontend/src/components/UseCasesTable.jsx`
- `frontend/src/components/ResultCards.jsx`
- `frontend/src/components/ChartPanel.jsx`

### Vai trò

- `ActorsTable.jsx`
  - hiển thị bảng actor

- `UseCasesTable.jsx`
  - hiển thị bảng use case

- `ResultCards.jsx`
  - hiển thị `UAW`, `UUCW`, `UCP`, `Effort`, `Schedule`

- `ChartPanel.jsx`
  - hiển thị biểu đồ phân bố độ phức tạp

## 17. Test dùng để chứng minh gì

### File chính

- `backend/tests/test_api.py`
- `backend/tests/test_llm_extractor.py`
- `backend/tests/test_ucp_calculator.py`

### Ý nghĩa

- `test_api.py`
  - chứng minh API backend chạy đúng end-to-end

- `test_llm_extractor.py`
  - chứng minh parser, normalization, classifier hoạt động đúng
  - đặc biệt hữu ích khi demo file `.docx` hoặc SRS
  - có test hồi quy cho template IEEE/SRS

- `test_ucp_calculator.py`
  - chứng minh công thức UCP, effort, schedule đúng

Nếu bị hỏi “làm sao chứng minh hệ thống chạy đúng?”, bạn có thể trả lời:

> Em có test ở 3 lớp: lớp API, lớp extraction-normalization, và lớp UCP calculator. Nhờ vậy em kiểm tra được từ parser tài liệu đến công thức tính cuối cùng.

## 18. Câu trả lời nhanh khi bị hỏi “file nào làm gì?”

- nhận request backend:
  - `backend/app/api/routes/analysis.py`

- đọc file upload:
  - `backend/app/utils/file_reader.py`

- parser SRS / use case document:
  - `backend/app/utils/use_case_document_parser.py`

- trích xuất actor/use case:
  - `backend/app/services/llm_extractor.py`

- chuẩn hóa dữ liệu:
  - `backend/app/utils/normalization.py`

- phân loại actor theo chuẩn UCP:
  - `backend/app/services/actor_classifier.py`

- phân loại use case theo transaction count:
  - `backend/app/services/use_case_classifier.py`

- tính UCP:
  - `backend/app/services/ucp_calculator.py`

- giao diện chính:
  - `frontend/src/pages/HomePage.jsx`

- gọi API từ frontend:
  - `frontend/src/api/client.js`

## 19. Kết luận

Điểm mạnh của project là tách khá rõ thành các lớp:

- `Frontend`
  - nhập liệu và hiển thị

- `Extraction layer`
  - lấy actor và use case từ text hoặc tài liệu có cấu trúc

- `Normalization layer`
  - làm sạch dữ liệu theo rule UCP

- `Calculation layer`
  - tính UCP, Effort, Schedule

Kiểu tổ chức này giúp project:
- dễ đọc
- dễ demo
- dễ bảo vệ
- dễ sửa khi thay domain
- dễ mở rộng sau này nếu muốn nối LLM thật
