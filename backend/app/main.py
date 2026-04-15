"""Điểm khởi động chính của ứng dụng FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router

# Tạo đối tượng ứng dụng FastAPI.
app = FastAPI(
    title="Công cụ ước lượng Use Case Point tự động",
    version="0.1.0",
    description="Backend đơn giản cho prototype trích xuất và tính toán UCP.",
)

# Bật CORS để frontend React ở máy local có thể gọi API backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Nạp toàn bộ router API vào ứng dụng chính.
app.include_router(api_router)
