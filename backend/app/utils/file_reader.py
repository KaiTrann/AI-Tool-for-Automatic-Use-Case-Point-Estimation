"""Các hàm hỗ trợ đọc file tải lên.

Project này ưu tiên prototype đơn giản:
- File upload được xử lý như nguồn text bổ sung
- Không phân tích formal use case specification template
- Không parse thật cấu trúc nhị phân của file .docx trong phiên bản hiện tại
"""

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

    try:
        # Ưu tiên UTF-8 vì đây là encoding phổ biến nhất cho file text hiện nay.
        decoded_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Nếu không decode được bằng UTF-8 thì fallback sang latin-1
        # để giảm khả năng hệ thống bị lỗi khi người dùng upload file khác chuẩn.
        decoded_text = file_bytes.decode("latin-1", errors="ignore")

    return uploaded_file.filename, decoded_text
