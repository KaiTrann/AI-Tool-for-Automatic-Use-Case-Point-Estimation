"""Helper chuẩn hóa actor string lấy từ SRS / Use Case Document.

File này chỉ làm một việc:
- biến chuỗi actor thô trong tài liệu thành danh sách actor sạch

Ví dụ:
- "Users of the system, including: Librarian, Stocker"
-> ["Librarian", "Stocker"]

Mục tiêu:
- tránh để parser chính phải tự xử lý nhiều trường hợp string bẩn
- giúp việc classify actor ở bước sau ổn định hơn
"""

from __future__ import annotations

import re

from app.utils.parser import normalize_name

ACTOR_PREFIX_PATTERNS = (
    # Các mẫu prefix thường gặp trong SRS nhưng không phải là tên actor thật.
    r"^users? of the system,\s*including:\s*",
    r"^users? of the system including:\s*",
    r"^including:\s*",
    r"^all actor[s]?:\s*",
    r"^actor[s]?:\s*",
)


def normalize_actor_list(actor_text: str | None) -> list[str]:
    """Chuẩn hóa một field actor thành danh sách actor sạch."""
    if not actor_text:
        return []

    # Bước 1:
    # làm sạch chuỗi tổng ban đầu trước khi tách.
    cleaned_text = normalize_name(actor_text)
    cleaned_text = _remove_actor_prefixes(cleaned_text)
    cleaned_text = cleaned_text.strip(" .,:;-")
    if not cleaned_text:
        return []

    # Bước 2:
    # tách một chuỗi actor thành nhiều actor riêng bằng các dấu nối phổ biến.
    parts = re.split(r",| and | & |;", cleaned_text, flags=re.IGNORECASE)
    actors: list[str] = []

    for part in parts:
        # Mỗi actor con lại được làm sạch thêm một lần nữa
        # vì có thể prefix như "Including:" xuất hiện ở từng mảnh nhỏ.
        cleaned_part = normalize_name(part).strip(" .,:;-")
        cleaned_part = _remove_actor_prefixes(cleaned_part).strip(" .,:;-")
        if not cleaned_part:
            continue
        actors.append(cleaned_part)

    return _deduplicate_strings(actors)


def _remove_actor_prefixes(value: str) -> str:
    """Xóa các tiền tố thừa kiểu 'Including:' hay 'All Actor:'."""
    cleaned_value = value
    for pattern in ACTOR_PREFIX_PATTERNS:
        # Áp regex nhiều lần để bỏ hết các cụm mô tả không phải tên actor.
        cleaned_value = re.sub(pattern, "", cleaned_value, flags=re.IGNORECASE)
    return normalize_name(cleaned_value)


def _deduplicate_strings(values: list[str]) -> list[str]:
    """Loại trùng nhưng giữ nguyên thứ tự xuất hiện."""
    seen: set[str] = set()
    unique_values: list[str] = []

    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_values.append(value)

    return unique_values
