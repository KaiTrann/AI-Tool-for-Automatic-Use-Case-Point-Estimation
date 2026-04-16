"""Các hàm hỗ trợ đọc file tải lên.

Phiên bản hiện tại ưu tiên:
- đọc text thuần (.txt, .md)
- đọc Use Case Document dạng .docx
- hỗ trợ best-effort cho file .doc cũ
"""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from fastapi import UploadFile


async def read_uploaded_text(uploaded_file: UploadFile | None) -> tuple[str | None, str | None]:
    """Đọc file tải lên dưới dạng text với cơ chế decode đơn giản.

    Hàm này phù hợp cho:
    - file .txt
    - file .md
    - nội dung text mock gửi lên với tên file .docx
    """
    if uploaded_file is None:
        return None, None

    # Đọc toàn bộ nội dung file vào bộ nhớ.
    # Với prototype học thuật, cách này là đủ đơn giản và dễ hiểu.
    file_bytes = await uploaded_file.read()
    if not file_bytes:
        return uploaded_file.filename, ""

    file_name = uploaded_file.filename or "uploaded_file"
    extension = Path(file_name).suffix.lower()

    if extension == ".docx":
        return file_name, _read_docx_text(file_bytes)

    if extension == ".doc":
        return file_name, _read_legacy_doc_text(file_bytes)

    try:
        # Ưu tiên UTF-8 vì đây là encoding phổ biến nhất cho file text hiện nay.
        decoded_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Nếu không decode được bằng UTF-8 thì fallback sang latin-1
        # để giảm khả năng hệ thống bị lỗi khi người dùng upload file khác chuẩn.
        decoded_text = file_bytes.decode("latin-1", errors="ignore")

    return file_name, decoded_text


def _read_docx_text(file_bytes: bytes) -> str:
    """Đọc text từ file .docx bằng cách mở XML bên trong file nén."""
    try:
        with ZipFile(BytesIO(file_bytes)) as archive:
            document_xml = archive.read("word/document.xml")
    except (BadZipFile, KeyError):
        # Nếu file .docx lỗi cấu trúc, fallback sang cơ chế đọc text thô.
        return _read_legacy_doc_text(file_bytes)

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ElementTree.fromstring(document_xml)
    paragraphs: list[str] = []

    for paragraph in root.findall(".//w:p", namespace):
        text_parts = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
            if node.text
        ]
        paragraph_text = "".join(text_parts).strip()
        if paragraph_text:
            paragraphs.append(paragraph_text)

    return "\n".join(paragraphs)


def _read_legacy_doc_text(file_bytes: bytes) -> str:
    """Best-effort đọc text từ file .doc cũ.

    File .doc nhị phân rất khó parse hoàn chỉnh nếu không dùng thư viện ngoài.
    Ở prototype này, mình lấy các chuỗi ký tự đọc được để phục vụ demo tài liệu mẫu.
    """
    decoded_text = file_bytes.decode("latin-1", errors="ignore")
    normalized_text = decoded_text.replace("\x00", " ")

    candidate_lines = re.findall(r"[A-Za-z0-9][A-Za-z0-9\s,.:;()/_-]{3,}", normalized_text)
    cleaned_lines: list[str] = []
    seen: set[str] = set()

    for line in candidate_lines:
        compact_line = " ".join(line.split()).strip()
        if len(compact_line) < 4:
            continue
        if compact_line.lower() in seen:
            continue
        seen.add(compact_line.lower())
        cleaned_lines.append(compact_line)

    return "\n".join(cleaned_lines)
