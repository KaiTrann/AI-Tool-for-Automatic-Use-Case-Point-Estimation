"""Các hàm tiện ích để xử lý và chuẩn hóa text đầu vào."""

import re


def combine_text_sources(source_text: str | None, file_text: str | None) -> str:
    """Ghép text nhập tay và text đọc từ file thành một chuỗi duy nhất."""
    parts = [part.strip() for part in [source_text or "", file_text or ""] if part and part.strip()]
    return "\n".join(parts)


def split_sentences(text: str) -> list[str]:
    """Tách đoạn văn thành các câu ngắn để phục vụ trích xuất use case."""
    if not text.strip():
        return []
    raw_parts = re.split(r"[.\n]+", text)
    return [part.strip() for part in raw_parts if part.strip()]


def sentence_to_use_case_name(sentence: str, index: int) -> str:
    """Biến một câu thành tên use case ngắn gọn, dễ đọc."""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", sentence).strip()
    words = cleaned.split()
    if not words:
        return f"Use Case {index}"
    return " ".join(words[:6]).title()


def guess_actor_complexity(actor_name: str) -> str:
    """Đoán độ phức tạp của actor bằng một luật đơn giản."""
    lowered = actor_name.lower()
    if lowered in {"admin", "manager", "system"}:
        return "complex"
    if lowered in {"student", "customer", "staff"}:
        return "average"
    return "simple"


def guess_use_case_complexity(sentence: str) -> str:
    """Đoán độ phức tạp của use case từ độ dài câu và từ khóa."""
    lowered = sentence.lower()
    word_count = len(lowered.split())
    complex_keywords = {"report", "analyze", "integrate", "calculate", "estimate", "dashboard"}

    if any(keyword in lowered for keyword in complex_keywords) or word_count >= 14:
        return "complex"
    if word_count >= 8:
        return "average"
    return "simple"


def normalize_name(name: str) -> str:
    """Chuẩn hóa tên bằng cách xóa khoảng trắng thừa."""
    return " ".join(name.split()).strip()
