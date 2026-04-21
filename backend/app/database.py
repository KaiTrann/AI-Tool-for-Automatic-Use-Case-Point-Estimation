"""Helper kết nối MySQL cho backend.

File này chỉ chịu trách nhiệm tạo kết nối database.
Các câu SQL insert/select nằm trong repository để code dễ đọc và dễ bảo vệ đồ án.
"""

# Cho phép dùng annotation kiểu mới mà không bị lỗi khi Python đánh giá type hint sớm.
from __future__ import annotations

# Module os dùng để đọc biến môi trường như UCP_DB_HOST, UCP_DB_PORT...
import os

# Any dùng cho dict cấu hình vì giá trị có thể là str, int hoặc bool.
from typing import Any


def get_database_config() -> dict[str, Any]:
    """Lấy cấu hình MySQL từ biến môi trường, nếu không có thì dùng cấu hình demo mặc định."""
    # Trả về dict đúng format mà mysql.connector.connect(...) cần.
    return {
        # Host MySQL theo yêu cầu demo của project.
        "host": os.getenv("UCP_DB_HOST", "localhost"),
        # Port đang dùng là 3307, khác port MySQL mặc định 3306.
        "port": int(os.getenv("UCP_DB_PORT", "3307")),
        # Tài khoản MySQL demo.
        "user": os.getenv("UCP_DB_USER", "khanh"),
        # Mật khẩu MySQL demo.
        "password": os.getenv("UCP_DB_PASSWORD", "khanhcute2306"),
        # Database lưu kết quả phân tích UCP.
        "database": os.getenv("UCP_DB_NAME", "ucpdb"),
        # UTF-8 đầy đủ để lưu được tiếng Việt trong SRS/use case document.
        "charset": "utf8mb4",
        # dictionary=True giúp SELECT trả về dict, dễ serialize JSON cho API.
        "use_unicode": True,
    }


def get_connection():
    """Tạo một connection MySQL mới.

    mysql.connector được import bên trong hàm để:
    - project vẫn import được khi máy chưa cài package database
    - test cũ không bị fail chỉ vì chưa bật MySQL
    """
    # Bắt lỗi import để báo hướng dẫn cài package rõ ràng cho sinh viên.
    try:
        # Import thư viện MySQL chính thức đang khai báo trong requirements.txt.
        import mysql.connector
    except ImportError as error:
        # Nếu package chưa cài, báo lỗi dễ hiểu thay vì lỗi Python khó đọc.
        raise RuntimeError(
            "Chưa cài mysql-connector-python. Hãy chạy: python -m pip install -r requirements.txt"
        ) from error

    # Lấy cấu hình DB từ hàm riêng để dễ đổi khi chuyển sang máy khác.
    config = get_database_config()

    # Tạo connection thật tới MySQL; repository sẽ tự đóng connection sau khi dùng xong.
    return mysql.connector.connect(**config)
