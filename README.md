# AI Tool for Automatic Use Case Point Estimation

Đây là một prototype học thuật cho đồ án môn học về **Use Case Point (UCP)**.

Hệ thống nhận:
- `Requirements Text`
- `Use Case Description`
- hoặc nội dung text từ file upload

Sau đó hệ thống:
- trích xuất `Actor`
- trích xuất `Use Case`
- chuẩn hóa dữ liệu extraction
- tính `UAW`, `UUCW`, `UUCP`, `UCP`, `Effort`, `Schedule`

Project dùng:
- **Backend**: FastAPI + Python
- **Frontend**: React + Vite
- **Chart**: Chart.js

## 1. Mục tiêu của README này

README này được viết theo hướng:
- người khác cầm project trên **máy lạ / máy mới** vẫn chạy được
- tránh xung đột:
  - Python global
  - pip global
  - virtual environment cũ
  - Node/npm cũ
  - chạy sai thư mục

Nếu bạn chỉ cần làm đúng một nguyên tắc quan trọng nhất, hãy nhớ:

> **Không cài package Python bằng pip global cho project này. Luôn dùng `backend/.venv` và luôn dùng `python -m pip`.**

---

## 2. Cấu trúc project

```text
AI Tool for Automatic UCPE/
|-- backend/
|   |-- app/
|   |-- tests/
|   `-- requirements.txt
|-- frontend/
|   |-- src/
|   |-- package.json
|   `-- vite.config.js
|-- PROJECT_STRUCTURE_VI.md
|-- THUYET_MINH_CODE_VI.md
`-- README.md
```

Tài liệu thêm:
- [PROJECT_STRUCTURE_VI.md](./PROJECT_STRUCTURE_VI.md): bản đồ từng folder và file
- [THUYET_MINH_CODE_VI.md](./THUYET_MINH_CODE_VI.md): thuyết minh luồng chạy từ input đến UCP

---

## 3. Yêu cầu trên máy mới

### Bắt buộc

1. **Python 3.12 hoặc 3.13**
2. **Node.js 18+**
3. **npm** đi kèm Node.js

### Khuyến nghị

4. **Git**
5. **VS Code**

### Cách kiểm tra

Mở PowerShell hoặc Command Prompt và chạy:

```powershell
python --version
node --version
npm --version
```

Kỳ vọng:
- Python có version `3.12.x` hoặc `3.13.x`
- Node có version `18+`

Nếu máy có nhiều Python:

```powershell
py --version
py -0
```

---

## 4. Quy tắc tránh xung đột môi trường

### Với Python

Project này chỉ nên cài package vào:

```text
backend/.venv
```

Không nên:
- `pip install fastapi` ở global
- `pip install -r requirements.txt` ở thư mục ngoài project
- dùng `.venv` ở root project khác

Luôn dùng:

```powershell
python -m pip install ...
```

thay vì:

```powershell
pip install ...
```

Lý do:
- `pip` có thể trỏ nhầm sang Python khác
- `python -m pip` chắc chắn đi cùng interpreter đang dùng

### Với Node.js

Frontend chỉ cài package trong:

```text
frontend/node_modules
```

Không copy `node_modules` từ project khác vào.

Nếu frontend lỗi package:
- xóa `frontend/node_modules`
- xóa `frontend/package-lock.json` nếu thật sự cần làm sạch sâu
- rồi chạy lại `npm install`

---

## 5. Cài backend từ đầu trên máy mới

### Bước 1: vào đúng thư mục backend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
```

Nếu bạn clone hoặc copy project sang chỗ khác thì chỉ cần thay đường dẫn cho đúng.

### Bước 2: tạo virtual environment riêng cho backend

```powershell
python -m venv .venv
```

Nếu máy có nhiều bản Python và muốn chỉ rõ:

```powershell
py -3.13 -m venv .venv
```

### Bước 3: activate virtual environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Command Prompt:

```cmd
.venv\Scripts\activate.bat
```

Sau khi activate, terminal thường sẽ hiện thêm:

```text
(.venv)
```

ở đầu dòng lệnh.

### Bước 4: nâng pip

```powershell
python -m pip install --upgrade pip
```

### Bước 5: cài package cho backend

```powershell
python -m pip install -r requirements.txt
```

### Bước 6: chạy backend

```powershell
uvicorn app.main:app --reload
```

Kỳ vọng:
- backend chạy ở `http://127.0.0.1:8000`
- mở `http://127.0.0.1:8000/docs` sẽ thấy Swagger UI

### Bước 7: kiểm tra nhanh backend

Mở trình duyệt:

```text
http://127.0.0.1:8000/health
```

Kỳ vọng:

```json
{
  "status": "ok",
  "service": "backend-uoc-luong-ucp"
}
```

---

## 6. Cài frontend từ đầu trên máy mới

### Bước 1: mở terminal mới và vào thư mục frontend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\frontend"
```

### Bước 2: cài package

```powershell
npm install
```

### Bước 3: chạy frontend

```powershell
npm run dev
```

Kỳ vọng:
- frontend chạy ở `http://localhost:5173`

### Bước 4: mở giao diện

Mở trình duyệt:

```text
http://localhost:5173
```

Frontend mặc định gọi backend ở:

```text
http://localhost:8000
```

Vì vậy backend phải chạy trước hoặc chạy cùng lúc.

---

## 7. Cách chạy project đầy đủ trên máy mới

Bạn cần **2 terminal**.

### Terminal 1: backend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Terminal 2: frontend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\frontend"
npm install
npm run dev
```

Sau đó mở:

```text
http://localhost:5173
```

---

## 8. Nếu project đã có sẵn môi trường rồi thì chạy nhanh

Nếu project đã cài sẵn từ trước và thư mục `backend/.venv` + `frontend/node_modules` vẫn còn dùng tốt:

### Backend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

### Frontend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\frontend"
npm run dev
```

---

## 9. Chạy test và build

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

---

## 10. LLM Mode là gì

Frontend có mục `LLM Mode` với 2 lựa chọn:

### `Mock Mode`

- dùng extractor nội bộ theo rule
- không gọi LLM thật
- phù hợp để demo ổn định trên lớp
- không cần API key

### `Placeholder API Mode`

- hiện chưa gọi LLM thật
- nhưng backend vẫn build prompt để giữ sẵn kiến trúc tích hợp LLM
- phù hợp để giải thích rằng project có thể nâng cấp sang AI thật sau này

File liên quan:
- `backend/app/services/llm_extractor.py`
- `backend/app/services/prompt_templates.py`
- `frontend/src/pages/HomePage.jsx`

---

## 11. Các lỗi thường gặp và cách xử lý

### Lỗi 1: `No module named fastapi`

Nguyên nhân:
- chưa activate `backend/.venv`
- hoặc đang dùng sai Python

Cách xử lý:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Lỗi 2: `pip` cài nhầm sang Python khác

Nguyên nhân:
- dùng `pip install ...` thay vì `python -m pip install ...`

Cách xử lý đúng:

```powershell
python -m pip install -r requirements.txt
```

### Lỗi 3: PowerShell chặn activate script

Nếu gặp lỗi Execution Policy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Rồi activate lại:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Lỗi 4: `npm install` lỗi hoặc frontend không lên

Cách xử lý:

```powershell
cd frontend
Remove-Item -Recurse -Force node_modules
npm install
npm run dev
```

### Lỗi 5: frontend lên nhưng không gọi được backend

Kiểm tra:
- backend có đang chạy ở `http://localhost:8000` không
- mở `http://localhost:8000/health` xem có trả `status: ok` không

### Lỗi 6: giải nén project xong bị lồng folder

Chỉ nên dùng đúng folder có cấu trúc:

```text
AI Tool for Automatic UCPE/
  backend/
  frontend/
  README.md
```

Không chạy ở folder ngoài nếu bên trong còn một lớp `AI Tool for Automatic UCPE` nữa.

---

## 12. Làm sạch môi trường nếu chạy lỗi nặng

Nếu máy bị rối môi trường, có thể làm sạch như sau.

### Làm sạch backend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\backend"
deactivate
Remove-Item -Recurse -Force .venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Làm sạch frontend

```powershell
cd "D:\Repositories\AI Tool for Automatic UCPE\frontend"
Remove-Item -Recurse -Force node_modules
Remove-Item -Force package-lock.json
npm install
```

Chỉ xóa `package-lock.json` khi bạn thật sự muốn cài lại toàn bộ dependency từ đầu.

---

## 13. Danh sách dependency hiện tại

### Backend

Trong `backend/requirements.txt`:
- fastapi
- uvicorn
- pydantic
- python-multipart
- pytest
- httpx

### Frontend

Trong `frontend/package.json`:
- react
- react-dom
- chart.js
- react-chartjs-2
- vite
- @vitejs/plugin-react

---

## 14. Ghi chú kỹ thuật

- Phiên bản hiện tại chưa parse nhị phân `.docx` thật
- File upload hiện được xử lý như nguồn text đơn giản
- Project tập trung vào **UCP estimation từ free-text requirements**
- Đây là prototype học thuật, ưu tiên:
  - dễ đọc
  - dễ demo
  - dễ giải thích

---

## 15. Khi cần giải thích code

Nếu cần hiểu từng folder/file:
- xem [PROJECT_STRUCTURE_VI.md](./PROJECT_STRUCTURE_VI.md)

Nếu cần thuyết trình luồng chạy từ input đến output:
- xem [THUYET_MINH_CODE_VI.md](./THUYET_MINH_CODE_VI.md)
