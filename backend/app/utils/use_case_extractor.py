"""Helper lấy tên use case sạch từ block SRS / Use Case Document.

File này chịu trách nhiệm:
- lấy đúng tên use case từ field chính thức
- fallback sang UC header nếu thiếu field
- chặn các chuỗi rác như metadata, TOC, caption hình

Mục tiêu:
- tên use case phải ngắn, sạch, đúng business function
- không lấy nhầm "Created by" hay dòng trong Table of Contents
"""

from __future__ import annotations

import re

from app.utils.parser import normalize_name

IGNORED_USE_CASE_NAME_VALUES = (
    # Các field metadata tuyệt đối không được dùng làm tên use case.
    "create by",
    "created by",
    "last updated by",
    "date created",
    "date last updated",
)

UC_HEADER_PATTERNS = (
    # Hỗ trợ nhiều kiểu header trong tài liệu thật:
    # - UC 01: Login
    # - UC.02 Search books
    # - Use Case 1: Book Room
    re.compile(r"^\s*UC[\.\s]?\d+\s*:\s*(.+)$", re.IGNORECASE),
    re.compile(r"^\s*UC[\.\s]?\d+\s+(.+)$", re.IGNORECASE),
    re.compile(r"^\s*Use Case\s+\d+\s*:\s*(.+)$", re.IGNORECASE),
)


def extract_use_case_name(
    explicit_name: str | None,
    header_line: str | None,
) -> str | None:
    """Lấy tên use case ưu tiên từ field 'Use case name', fallback sang UC header."""
    # Ưu tiên số 1:
    # nếu tài liệu có field "Use case name" thì luôn dùng field này.
    explicit_candidate = _clean_use_case_name(explicit_name)
    if explicit_candidate:
        return explicit_candidate

    if not header_line:
        return None

    # Fallback:
    # nếu thiếu field chính thức thì cố lấy từ header UC.
    normalized_header = normalize_name(header_line)
    for pattern in UC_HEADER_PATTERNS:
        match = pattern.match(normalized_header)
        if match:
            return _clean_use_case_name(match.group(1))

    return None


def looks_like_invalid_use_case_name(value: str | None) -> bool:
    """Kiểm tra một chuỗi có phải tên use case không hợp lệ hay không."""
    if not value:
        return True

    lowered_value = normalize_name(value).lower()
    if lowered_value in IGNORED_USE_CASE_NAME_VALUES:
        return True

    # Bỏ các chuỗi mô tả section không phải business function.
    if re.search(r"table of contents|list of use cases|revision history", lowered_value):
        return True

    # Bỏ caption kiểu Figure / Diagram / Image.
    if re.search(r"^(figure|fig\.|diagram|image)\b", lowered_value):
        return True

    return False


def _clean_use_case_name(value: str | None) -> str | None:
    """Làm sạch tên use case."""
    if not value:
        return None

    cleaned_value = normalize_name(value).strip(" .,:;-")
    # Sau khi làm sạch, nếu chuỗi vẫn thuộc nhóm không hợp lệ
    # thì không được dùng làm tên use case.
    if not cleaned_value or looks_like_invalid_use_case_name(cleaned_value):
        return None

    return cleaned_value
