# Thuyết Minh Code AI Tool for Automatic UCPE

Tài liệu này giải thích luồng chạy của hệ thống theo cách dễ trình bày:
- người dùng nhập dữ liệu ở đâu
- frontend xử lý gì
- backend xử lý gì
- extraction chạy như thế nào
- normalization làm gì
- UCP được tính ra sao
- kết quả quay lại giao diện thế nào

Mục tiêu là để khi bảo vệ đồ án, bạn có thể kể lại luồng chạy một cách logic và chỉ đúng file nếu bị hỏi sâu.

## 1. Mục tiêu của hệ thống

Hệ thống này dùng để hỗ trợ **Use Case Point Estimation** từ dữ liệu đầu vào mà người dùng cung cấp.

Đầu vào hiện tại có thể là:
- Requirements Text dạng văn bản thường
- Use Case Description ngắn
- Use Case Document theo template
- file upload `.txt`, `.docx`, `.doc`

Đầu ra của hệ thống gồm:
- danh sách `actors`
- danh sách `use_cases`
- `UAW`
- `UUCW`
- `UUCP`
- `UCP`
- `Effort`
- `Schedule`

Điểm quan trọng:
- project có thể đọc văn bản tự nhiên
- đồng thời cũng hỗ trợ đọc Use Case Document theo template khi người dùng upload file Word hoặc dán nội dung template vào ô nhập

## 2. Luồng tổng quát từ đầu vào đến kết quả

Luồng chạy tổng quát của hệ thống như sau:

1. Người dùng nhập text hoặc chọn file trên frontend.
2. Frontend gửi dữ liệu sang backend bằng API.
3. Backend đọc text và nội dung file upload.
4. Backend đưa dữ liệu vào `llm_extractor.py` để lấy actor và use case.
5. Kết quả extraction đi qua `normalization.py` để làm sạch và chuẩn hóa.
6. Dữ liệu đã chuẩn hóa được đưa vào `ucp_calculator.py` để tính UCP.
7. Backend tính tiếp `Effort` và `Schedule`.
8. Backend trả kết quả về frontend.
9. Frontend hiển thị bảng actor, bảng use case, result cards và biểu đồ.

Nếu cần nói ngắn gọn khi thuyết trình, bạn có thể nói:

> Hệ thống của em gồm 3 lớp chính: extraction, normalization và calculation. Frontend chỉ nhập liệu và hiển thị; còn backend chịu trách nhiệm đọc dữ liệu, trích xuất actor/use case, làm sạch dữ liệu và tính ra UCP, Effort, Schedule.

## 3. Bước 1: Người dùng nhập dữ liệu ở frontend

### File chính

- `frontend/src/pages/HomePage.jsx`

### Vai trò

Đây là trang chính của hệ thống. Người dùng thao tác chủ yếu ở đây.

Trên giao diện hiện có:
- ô nhập nội dung Use Case Document hoặc Requirements Text
- ô chọn file upload
- dropdown chọn `LLM Mode`
- các ô nhập `TCF`, `ECF`, `Productivity Factor`, `Team Size`
- nút `Extract`
- nút `Calculate`

### Hai luồng chính từ frontend

#### Luồng 1: chỉ trích xuất

Khi người dùng bấm `Extract`:
- frontend gọi `POST /extract`
- mục tiêu là lấy danh sách actor và use case
- chưa tính UCP

#### Luồng 2: trích xuất và tính toán

Khi người dùng bấm `Calculate`:
- nếu dữ liệu extraction cũ còn hợp lệ thì frontend gọi `POST /ucp/calculate`
- nếu text/file vừa thay đổi hoặc chưa extract trước đó thì frontend gọi `POST /analyze-and-calculate`

Ý nghĩa:
- tránh gọi extraction lại nhiều lần không cần thiết
- giao diện phản hồi nhanh hơn
- luồng nghiệp vụ tách rõ hơn

## 4. Bước 2: Frontend gọi backend

### File chính

- `frontend/src/api/client.js`

### Vai trò

File này gom tất cả lời gọi API vào một chỗ.

Các hàm chính:
- `checkHealth()`
- `extractData()`
- `calculateUCP()`
- `analyzeAndCalculate()`

### Lợi ích của cách làm này

- code frontend dễ đọc hơn
- dễ sửa địa chỉ API hơn
- dễ xử lý loading và error hơn
- dễ chứng minh khi bị hỏi “frontend gọi backend ở đâu?”

## 5. Bước 3: Backend nhận request

### File chính

- `backend/app/main.py`
- `backend/app/api/router.py`
- `backend/app/api/routes/analysis.py`
- `backend/app/api/routes/health.py`

### Vai trò từng file

- `main.py`
  - tạo app FastAPI
  - bật CORS
  - include router

- `router.py`
  - gom route `health` và `analysis`

- `health.py`
  - chứa `GET /health`

- `analysis.py`
  - chứa toàn bộ endpoint chính:
    - `POST /extract`
    - `POST /ucp/calculate`
    - `POST /analyze-and-calculate`

Nếu bị hỏi “API quan trọng nhất nằm ở đâu?”, câu trả lời là:
- `backend/app/api/routes/analysis.py`

## 6. Bước 4: Backend đọc text và file upload

### File chính

- `backend/app/api/routes/analysis.py`
- `backend/app/utils/file_reader.py`
- `backend/app/utils/parser.py`

### Luồng xử lý

Khi backend nhận request:

1. lấy text do người dùng nhập
2. nếu có file upload thì đọc file
3. chuyển nội dung file thành text
4. ghép text nhập tay và text từ file thành một chuỗi chung

### `file_reader.py` làm gì

File này chịu trách nhiệm đọc file upload và chuyển về text.

Hiện tại file hỗ trợ:
- `.txt`
- `.md`
- `.docx`
- `.doc` theo kiểu best-effort

Ý nghĩa:
- nếu người dùng không muốn gõ tay mà muốn upload Use Case Document thì backend vẫn xử lý được

### `parser.py` làm gì

File này có các helper cơ bản:
- `combine_text_sources()`
  - ghép nhiều nguồn text
- `normalize_name()`
  - chuẩn hóa khoảng trắng
- `split_sentences()`
  - tách câu

## 7. Bước 5: Backend chọn LLM Mode

### File chính

- `backend/app/services/llm_extractor.py`
- `backend/app/services/prompt_templates.py`

### `LLM Mode` có tác dụng gì

Đây là nơi dropdown `LLM Mode` trên frontend thực sự ảnh hưởng đến hệ thống.

Trong `llm_extractor.py`, hàm:
- `extract_requirements()`

sẽ gọi:
- `_generate_extraction_json(text, mode)`

Tại đây backend chọn nhánh xử lý theo mode.

### `Mock Mode`

- không gọi LLM thật
- dùng extractor rule-based nội bộ
- phù hợp để demo ổn định
- không cần Internet hay API key

### `Placeholder API Mode`

- chưa gọi LLM thật
- nhưng vẫn build prompt qua `prompt_templates.py`
- giữ sẵn kiến trúc để sau này thay bằng API thật

Nói ngắn gọn:

> LLM Mode dùng để chọn nhánh trích xuất. Mock Mode phục vụ demo ổn định. Placeholder Mode mô phỏng vị trí tích hợp LLM thật trong tương lai.

## 8. Bước 6: Hệ thống phát hiện loại đầu vào

### File chính

- `backend/app/services/llm_extractor.py`

### Hai kiểu đầu vào chính

#### Kiểu 1: văn bản tự nhiên

Ví dụ:
- mô tả yêu cầu ngắn
- requirement paragraph
- use case description thường

Hệ thống sẽ:
- tách câu
- tìm actor
- tìm action
- sinh candidate use case

#### Kiểu 2: Use Case Document theo template

Ví dụ có các trường:
- `Use Case ID`
- `Use Case Name`
- `Primary Actor`
- `Secondary Actor`
- `Description`
- `Main Flow`
- `Alternative Flow`
- `Postconditions`

Hệ thống sẽ:
- nhận diện đây là template
- tách theo từng block `Use Case`
- lấy trực tiếp actor từ `Primary Actor` và `Secondary Actor`
- lấy use case name từ `Use Case Name`
- ước lượng complexity từ `Main Flow` và `Alternative Flow`

Điểm quan trọng:
- khi đã nhận ra đây là template thì backend không cố trích xuất kiểu “đoán từ câu tự nhiên” nữa
- như vậy kết quả sẽ sạch hơn

## 9. Bước 7: Extraction thô actor và use case

### File chính

- `backend/app/services/llm_extractor.py`

### Ý tưởng

Project chia extraction thành 2 tầng:

1. extraction thô
2. normalization làm sạch lại

Lý do:
- extraction ban đầu có thể chưa hoàn hảo
- normalization sẽ sửa lại để dữ liệu đủ sạch cho UCP

### Trích xuất actor

Các hàm liên quan:
- `_extract_raw_actors()`
- `_split_actor_names()`

Với text tự nhiên:
- backend dùng regex để tìm các mẫu như:
  - `The Customer can ...`
  - `The Administrator can ...`
  - `Payment Gateway ...`

Với template:
- backend lấy actor trực tiếp từ:
  - `Primary Actor`
  - `Secondary Actor`

### Trích xuất use case

Các hàm liên quan:
- `_extract_raw_use_cases()`
- `_split_action_sentence()`
- `_clean_raw_use_case_segment()`

Với text tự nhiên:
- backend tách câu
- cắt bỏ chủ ngữ
- tách nhiều action trong cùng một câu
- tạo danh sách use case thô

Ví dụ:

`The Customer can browse products, search products, and place order.`

sẽ được tách thành:
- `browse products`
- `search products`
- `place order`

Với template:
- backend lấy trực tiếp `Use Case Name`
- không cần đoán từ sentence fragment

## 10. Bước 8: Parse JSON extraction

### File chính

- `backend/app/utils/llm_json_parser.py`

### Vai trò

Sau khi extractor tạo JSON, backend không dùng ngay mà phải parse và validate lại.

Parser sẽ:
- kiểm tra JSON đúng cấu trúc hay không
- kiểm tra `complexity` có hợp lệ không
- chuẩn hóa tên và giá trị cơ bản

Ý nghĩa:
- tránh backend bị lỗi do JSON sai
- giữ schema nhất quán
- giúp bước normalization phía sau ổn định hơn

## 11. Bước 9: Normalization là lớp quan trọng nhất

### File chính

- `backend/app/utils/normalization.py`
- `backend/app/services/mapping_config.py`

Nếu bị hỏi:
- vì sao actor này bị bỏ
- vì sao use case này bị đổi tên
- vì sao complexity lại thành `complex`

thì phần lớn câu trả lời nằm ở hai file này.

### 11.1. Normalization actor

Các hàm chính:
- `normalize_actors()`
- `_normalize_actor_item()`

Rule chính:
- bỏ `System`
- human actor luôn là `complex`
- external actor luôn là `simple`
- chuẩn hóa tên actor như `Admin -> Administrator`
- loại actor trùng
- nếu có actor chung chung và actor cụ thể hơn thì giữ actor cụ thể hơn

Ví dụ:
- `Manager`
- `Hotel Manager`

thì giữ:
- `Hotel Manager`

### 11.2. Normalization use case

Các hàm chính:
- `normalize_use_cases()`
- `_normalize_use_case_item()`
- `_extract_canonical_use_case_name()`

Rule chính:
- đưa về dạng `Verb + Noun`
- giữ đúng domain noun
- loại sentence fragment
- loại internal step
- gộp sub-action thành use case cha
- loại trùng

Ví dụ:
- `update room availability`
- `delete room information`

có thể được gom thành:
- `Manage Room Information`

### 11.3. Loại internal step

Các hàm chính:
- `_is_internal_step()`
- `_is_background_processing_sentence()`

Rule:
- các hành vi nền như:
  - `Send Confirmation`
  - `Send Reminder`
  - `Notify User`
  - `Update Status`

sẽ bị loại khỏi use case list

Lý do:
- đây không phải business goal mà actor theo đuổi
- đây chỉ là hành vi nội bộ của hệ thống

### 11.4. Rule đặc biệt cho banking

Project đã được sửa thêm cho domain banking.

Điểm quan trọng:
- `Transfer Money`
- `Transfer Funds`
- `Transfer Payment`
- `Send Money`

phải luôn được hiểu là use case hợp lệ và được xếp `complex`

Lý do:
- đây là transactional workflow nhiều bước
- không được nhầm `Send Money` với `Send Confirmation`

Đây là lý do trong `normalization.py` có thêm rule ngoại lệ để:
- giữ lại `Send Money`
- nhưng vẫn loại `Send Confirmation`

### 11.5. Phân loại complexity

Hàm chính:
- `_classify_use_case_complexity()`

Thứ tự ưu tiên:
1. `complex`
2. `average`
3. `simple`

Ví dụ:

#### Simple
- `Login`
- `Search Rooms`
- `View Account Balance`
- `Check Status`

#### Average
- `Register`
- `Approve Transaction`
- `Confirm Orders`
- `Update Medical Notes`

#### Complex
- `Book Room`
- `Place Order`
- `Transfer Money`
- `Borrow Books`
- `Manage Products`

Điểm hay của classifier hiện tại:
- không chỉ nhìn domain
- mà nhìn action chính của use case

## 12. Bước 10: Dữ liệu được đưa vào bộ tính UCP

### File chính

- `backend/app/services/ucp_calculator.py`
- `backend/app/models/request_models.py`

Sau khi extraction đã normalize xong, backend tạo dữ liệu đầu vào cho module UCP.

Dữ liệu gồm:
- danh sách actor đã sạch
- danh sách use case đã sạch
- `TCF`
- `ECF`
- `productivity_factor`

Ý nghĩa:
- bộ tính UCP chỉ làm việc với dữ liệu đã normalize
- như vậy kết quả UAW, UUCW, UCP mới đáng tin hơn

## 13. Bước 11: Tính UCP

### File chính

- `backend/app/services/ucp_calculator.py`

### Công thức

#### Actor weight

- `simple = 1`
- `average = 2`
- `complex = 3`

#### Use case weight

- `simple = 5`
- `average = 10`
- `complex = 15`

#### UAW

`UAW = tổng trọng số actor`

#### UUCW

`UUCW = tổng trọng số use case`

#### UUCP

`UUCP = UAW + UUCW`

#### UCP

`UCP = UUCP * TCF * ECF`

#### Effort

`Effort = UCP * productivity_factor`

## 14. Bước 12: Tính Effort và Schedule

### File chính

- `backend/app/services/effort_estimation_service.py`
- `backend/app/services/schedule_estimation_service.py`

### Effort

File `effort_estimation_service.py` tính:

`effort = UCP * productivity_factor`

### Schedule

File `schedule_estimation_service.py` tính:

`schedule = effort_hours / (team_size * 160)`

Ý nghĩa:
- mặc định 1 người làm 160 giờ mỗi tháng
- nếu team size lớn hơn thì thời gian dự kiến giảm xuống

## 15. Bước 13: Backend trả kết quả về frontend

### Với `/extract`

Backend trả:
- `actors`
- `use_cases`
- `notes`

### Với `/ucp/calculate`

Backend trả:
- `ucp`
- `effort`
- `schedule`

### Với `/analyze-and-calculate`

Backend trả đầy đủ:
- `extraction`
- `ucp`
- `effort`
- `schedule`

## 16. Bước 14: Frontend hiển thị kết quả

### File chính

- `frontend/src/pages/HomePage.jsx`
- `frontend/src/components/ActorsTable.jsx`
- `frontend/src/components/UseCasesTable.jsx`
- `frontend/src/components/ResultCards.jsx`
- `frontend/src/components/ChartPanel.jsx`

### Vai trò từng component

- `ActorsTable.jsx`
  - hiển thị bảng actor

- `UseCasesTable.jsx`
  - hiển thị bảng use case

- `ResultCards.jsx`
  - hiển thị UAW, UUCW, UCP, Effort, Schedule

- `ChartPanel.jsx`
  - hiển thị biểu đồ phân bố độ phức tạp

## 17. Vai trò của test

### File chính

- `backend/tests/test_api.py`
- `backend/tests/test_llm_extractor.py`
- `backend/tests/test_ucp_calculator.py`

### Ý nghĩa

- `test_api.py`
  - chứng minh API hoạt động đúng end-to-end

- `test_llm_extractor.py`
  - chứng minh extraction và normalization hoạt động đúng
  - có cả test cho các domain như e-commerce, library, hotel, banking

- `test_ucp_calculator.py`
  - chứng minh công thức UCP đúng

Nếu bị hỏi “làm sao chứng minh hệ thống chạy đúng?”, bạn có thể nói:

> Em có test ở 3 tầng: test công thức UCP, test extraction-normalization, và test API end-to-end. Nhờ vậy em kiểm tra được từ logic nhỏ nhất đến toàn bộ luồng backend.

## 18. Câu trả lời nhanh khi bị hỏi “file nào làm gì?”

- nhập liệu và bấm nút:
  - `frontend/src/pages/HomePage.jsx`

- gọi API:
  - `frontend/src/api/client.js`

- route backend:
  - `backend/app/api/routes/analysis.py`

- đọc file `.docx/.doc`:
  - `backend/app/utils/file_reader.py`

- extraction:
  - `backend/app/services/llm_extractor.py`

- prompt placeholder:
  - `backend/app/services/prompt_templates.py`

- normalize và classify:
  - `backend/app/utils/normalization.py`
  - `backend/app/services/mapping_config.py`

- tính UCP:
  - `backend/app/services/ucp_calculator.py`

- tính effort:
  - `backend/app/services/effort_estimation_service.py`

- tính schedule:
  - `backend/app/services/schedule_estimation_service.py`

## 19. Kết luận

Điểm mạnh của project là tách rõ thành các lớp:

- frontend
  - nhập liệu và hiển thị

- extraction layer
  - lấy actor và use case từ text hoặc template

- normalization layer
  - làm sạch dữ liệu theo rule UCP

- calculation layer
  - tính UCP, Effort, Schedule

Cách tổ chức này giúp project:
- dễ đọc
- dễ giải thích
- dễ demo
- dễ sửa theo từng domain
- và dễ nâng cấp lên LLM thật trong tương lai
