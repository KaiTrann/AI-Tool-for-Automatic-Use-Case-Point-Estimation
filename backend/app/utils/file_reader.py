"""Các hàm hỗ trợ đọc file tải lên.

Phiên bản hiện tại ưu tiên:
- đọc text thuần (.txt, .md)
- đọc Use Case Document dạng .docx
- hỗ trợ best-effort cho file .doc cũ

Vai trò trong toàn hệ thống:
- frontend gửi file lên API
- route gọi `read_uploaded_text()`
- file này chuyển nội dung file thành text
- text sau đó mới được đưa sang parser/extraction pipeline
"""

# Cho phép dùng type hint hiện đại mà vẫn giữ code dễ đọc.
from __future__ import annotations

# Regex dùng cho phần đọc file .doc cũ theo kiểu best-effort.
import re

# BytesIO giúp biến bytes trong bộ nhớ thành file-like object để ZipFile đọc được.
from io import BytesIO

# Path dùng để lấy extension file như .txt, .docx, .doc.
from pathlib import Path

# ElementTree dùng để đọc XML bên trong file .docx.
from xml.etree import ElementTree

# .docx thực chất là file zip chứa nhiều file XML.
from zipfile import BadZipFile, ZipFile

# UploadFile là kiểu file upload của FastAPI.
from fastapi import UploadFile


async def read_uploaded_text(uploaded_file: UploadFile | None) -> tuple[str | None, str | None]:
    """Đọc file tải lên dưới dạng text với cơ chế decode đơn giản.

    Hàm này phù hợp cho:
    - file .txt
    - file .md
    - nội dung text mock gửi lên với tên file .docx
    """
    # Nếu người dùng không upload file, route vẫn chạy bình thường.
    # Trả về (None, None) để backend biết không có file bổ sung.
    if uploaded_file is None:
        return None, None

    # Đọc toàn bộ nội dung file vào bộ nhớ.
    # Với prototype học thuật, cách này là đủ đơn giản và dễ hiểu.
    # `await uploaded_file.read()` đọc toàn bộ file thành bytes.
    # Với prototype sinh viên, file demo thường nhỏ nên đọc toàn bộ là đủ đơn giản.
    file_bytes = await uploaded_file.read()

    # Nếu file rỗng, vẫn trả tên file để frontend/backend có thể hiển thị thông tin.
    if not file_bytes:
        return uploaded_file.filename, ""

    # Lấy tên file; nếu vì lý do nào đó thiếu tên thì dùng tên mặc định.
    file_name = uploaded_file.filename or "uploaded_file"

    # Lấy phần mở rộng file để chọn cách đọc phù hợp.
    # Ví dụ: "demo.docx" -> ".docx"
    extension = Path(file_name).suffix.lower()

    # File .docx cần đọc bằng XML bên trong file zip.
    if extension == ".docx":
        return file_name, _read_docx_text(file_bytes)

    # File .doc cũ là binary format khó đọc hơn, nên dùng best-effort.
    if extension == ".doc":
        return file_name, _read_legacy_doc_text(file_bytes)

    try:
        # Ưu tiên UTF-8 vì đây là encoding phổ biến nhất cho file text hiện nay.
        # utf-8-sig xử lý thêm trường hợp file có BOM ở đầu.
        decoded_text = file_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        # Nếu không decode được bằng UTF-8 thì fallback sang latin-1
        # để giảm khả năng hệ thống bị lỗi khi người dùng upload file khác chuẩn.
        decoded_text = file_bytes.decode("latin-1", errors="ignore")

    return file_name, decoded_text


def _read_docx_text(file_bytes: bytes) -> str:
    """Đọc text từ file .docx bằng cách mở XML bên trong file nén."""
    try:
        # File .docx thực chất là một file zip.
        # Nội dung văn bản chính thường nằm ở "word/document.xml".
        with ZipFile(BytesIO(file_bytes)) as archive:
            document_xml = archive.read("word/document.xml")
    except (BadZipFile, KeyError):
        # Nếu file .docx lỗi cấu trúc, fallback sang cơ chế đọc text thô.
        return _read_legacy_doc_text(file_bytes)

    # WordprocessingML dùng namespace XML; phải khai báo namespace thì mới tìm được tag w:p, w:t.
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    # Parse chuỗi XML thành cây XML để duyệt.
    root = ElementTree.fromstring(document_xml)

    # Mỗi paragraph trong Word sẽ được gom thành một dòng text.
    paragraphs: list[str] = []

    # w:p là paragraph trong Word.
    for paragraph in root.findall(".//w:p", namespace):
        # w:t là text node nằm bên trong paragraph.
        # Một paragraph có thể có nhiều w:t vì Word chia text theo run/style.
        text_parts = [
            node.text or ""
            for node in paragraph.findall(".//w:t", namespace)
            if node.text
        ]

        # Ghép các text part thành paragraph hoàn chỉnh.
        paragraph_text = "".join(text_parts).strip()

        # Bỏ paragraph rỗng để parser phía sau ít bị nhiễu.
        if paragraph_text:
            paragraphs.append(paragraph_text)

    # Trả mỗi paragraph trên một dòng, giúp parser nhận diện field/section dễ hơn.
    return "\n".join(paragraphs)


def _read_legacy_doc_text(file_bytes: bytes) -> str:
    """Best-effort đọc text từ file .doc cũ.

    File .doc nhị phân rất khó parse hoàn chỉnh nếu không dùng thư viện ngoài.
    Ở prototype này, mình lấy các chuỗi ký tự đọc được để phục vụ demo tài liệu mẫu.
    """
    # latin-1 ít khi lỗi decode, phù hợp cho best-effort khi không có thư viện đọc .doc chuyên dụng.
    decoded_text = file_bytes.decode("latin-1", errors="ignore")

    # File .doc binary thường có nhiều ký tự null; thay bằng khoảng trắng để regex dễ lọc.
    normalized_text = decoded_text.replace("\x00", " ")

    # Lấy các chuỗi có vẻ là text người đọc được.
    # Đây không phải parser .doc hoàn chỉnh, chỉ đủ cho demo/prototype.
    candidate_lines = re.findall(r"[A-Za-z0-9][A-Za-z0-9\s,.:;()/_-]{3,}", normalized_text)
    cleaned_lines: list[str] = []
    seen: set[str] = set()

    for line in candidate_lines:
        # Gom nhiều khoảng trắng liên tiếp thành một khoảng trắng.
        compact_line = " ".join(line.split()).strip()

        # Bỏ chuỗi quá ngắn vì thường là nhiễu.
        if len(compact_line) < 4:
            continue

        # Bỏ dòng trùng để output gọn hơn.
        if compact_line.lower() in seen:
            continue
        seen.add(compact_line.lower())
        cleaned_lines.append(compact_line)

    # Trả danh sách dòng text đọc được để pipeline tiếp tục xử lý.
    return "\n".join(cleaned_lines)
