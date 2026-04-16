"""Dịch vụ trích xuất actor và use case cho project UCP.

Kiến trúc extraction:
1. Layer 1: trích xuất dữ liệu thô từ free-text input
2. Layer 2: normalization làm sạch, gộp trùng và chuẩn hóa
3. Layer 3: UCP calculation dùng dữ liệu đã normalize

Project này chỉ làm việc với:
- Requirements Text
- Use Case Description ngắn
- Nội dung text lấy từ file upload
"""

from __future__ import annotations

import json
import re

from app.models.requests import ExtractRequest
from app.models.responses import ExtractionResponse
from app.services.mapping_config import ACTION_VERB_PATTERNS, VERB_CANONICAL_MAP
from app.services.prompt_templates import build_extraction_prompt
from app.utils.llm_json_parser import parse_llm_extraction_json
from app.utils.normalization import normalize_extraction_result
from app.utils.parser import combine_text_sources, normalize_name, split_sentences

ACTION_SENTENCE_PATTERN = re.compile(
    r"\b(can|may|must|should|will|allows|lets)\b",
    re.IGNORECASE,
)
USE_CASE_BLOCK_PATTERN = re.compile(
    r"Use Case\s+\d+\s*:\s*.+?(?=(?:\nUse Case\s+\d+\s*:)|\Z)",
    re.IGNORECASE | re.DOTALL,
)
TEMPLATE_SECTION_LABELS = (
    "Use Case ID",
    "Use Case Name",
    "Primary Actor",
    "Secondary Actor",
    "Description",
    "Preconditions",
    "Main Flow",
    "Alternative Flow",
    "Postconditions",
)


class LlmExtractionError(ValueError):
    """Lỗi khi quá trình trích xuất không tạo được dữ liệu hợp lệ."""


def extract_requirements(request_model: ExtractRequest) -> ExtractionResponse:
    """Trích xuất actor/use case từ free-text input và trả về dữ liệu đã chuẩn hóa."""
    # Bước 1:
    # Gộp text nhập tay và text đọc từ file thành một chuỗi duy nhất.
    # Cách làm này giúp các mode extraction đều xử lý trên cùng một nguồn dữ liệu.
    combined_text = combine_text_sources(request_model.source_text, request_model.file_text)

    # Bước 2:
    # Tùy theo LLM Mode mà chọn cách lấy JSON extraction.
    # - mock: chạy extractor rule-based nội bộ
    # - placeholder: mô phỏng chỗ sau này sẽ gọi LLM API thật
    raw_json = _generate_extraction_json(combined_text, request_model.llm_mode)

    try:
        # Bước 3:
        # Parse JSON trả về và biến nó thành danh sách ActorItem / UseCaseItem có validate.
        raw_actors, raw_use_cases = parse_llm_extraction_json(raw_json)
    except ValueError as error:
        raise LlmExtractionError(str(error)) from error

    # Bước 4:
    # Chuẩn hóa kết quả extraction để:
    # - bỏ System
    # - gộp trùng
    # - sửa tên use case về verb + noun
    # - phân loại lại complexity theo rule cố định
    normalization_source_text = ""
    if not _looks_like_use_case_template(combined_text):
        normalization_source_text = combined_text

    actors, use_cases = normalize_extraction_result(
        actors=raw_actors,
        use_cases=raw_use_cases,
        source_text=normalization_source_text,
    )

    # Bước 5:
    # Trả thêm notes để frontend hiển thị người dùng đang chạy mode nào.
    notes = _build_notes(request_model.llm_mode, request_model.file_name, combined_text)
    return ExtractionResponse(actors=actors, use_cases=use_cases, notes=notes)


def _generate_extraction_json(text: str, mode: str) -> str:
    """Chọn cách trích xuất dựa trên chế độ đang dùng."""
    # Đây chính là nơi LLM Mode có tác dụng:
    # nó quyết định backend sẽ dùng nhánh extractor nào.
    if mode == "mock":
        return _build_mock_extraction_json(text)
    if mode == "placeholder":
        return _call_placeholder_llm_api(text)
    raise LlmExtractionError("Chế độ trích xuất không hợp lệ. Hãy dùng 'mock' hoặc 'placeholder'.")


def _build_mock_extraction_json(text: str) -> str:
    """Sinh JSON thô bằng rule-based extraction để demo local."""
    if _looks_like_use_case_template(text):
        # Nếu đầu vào là Use Case Document theo template,
        # backend sẽ không trích xuất kiểu "tách câu tự do" nữa.
        # Thay vào đó, hệ thống đọc theo từng block Use Case để kết quả sạch hơn.
        return json.dumps(_extract_template_payload(text))

    # Mock mode hoàn toàn không phụ thuộc Internet hoặc API key.
    # Phù hợp để demo nhanh, ổn định và dễ kiểm thử.
    actors = _extract_raw_actors(text)
    use_cases = _extract_raw_use_cases(text)
    return json.dumps({"actors": actors, "use_cases": use_cases})


def _call_placeholder_llm_api(text: str) -> str:
    """Giữ chỗ cho bước gọi LLM API thật.

    Hiện tại vẫn dùng cùng extractor với mock mode để project chạy ổn định.
    Prompt mới được build sẵn để sau này có thể thay bằng API thật.
    """
    # Hiện tại project chưa gọi model thật.
    # Tuy nhiên mình vẫn build prompt ở đây để:
    # - giữ đúng kiến trúc sẽ dùng khi nâng cấp thật
    # - giúp dễ chứng minh trong báo cáo rằng hệ thống đã có sẵn chỗ nối LLM
    _ = build_extraction_prompt(text)
    return _build_mock_extraction_json(text)


def _extract_raw_actors(text: str) -> list[dict[str, str]]:
    """Layer 1: trích xuất raw actor candidate từ free text.

    Ở layer này chưa cố gắng normalize triệt để.
    Việc gộp trùng và phân loại chính xác được xử lý ở normalization layer.
    """
    actors: list[dict[str, str]] = []
    # Các regex này chỉ tìm "ứng viên thô".
    # Việc quyết định actor cuối cùng có hợp lệ hay không được xử lý ở normalization.
    actor_patterns = [
        r"allows\s+(?:the |a |an )?([A-Za-z][A-Za-z\s-]{0,50}?)\s+to\b",
        r"(?:The |A |An )([A-Za-z][A-Za-z\s-]{0,50}?)\s+(?:can|may|must|should|will)\b",
        r"(?:external\s+)?([A-Za-z][A-Za-z\s-]{0,50}?(?:service|gateway|api|provider|system))\s+(?:is used|handles|processes|sends|integrates)\b",
    ]

    for pattern in actor_patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            candidate_name = normalize_name(match)
            if not candidate_name:
                continue
            actors.append({"name": candidate_name, "complexity": "average"})

    return actors


def _extract_raw_use_cases(text: str) -> list[dict[str, str]]:
    """Layer 1: trích xuất raw use case candidate từ free text."""
    use_cases: list[dict[str, str]] = []

    # Tách từng câu để giảm việc regex ăn quá dài.
    for sentence in split_sentences(text):
        if not ACTION_SENTENCE_PATTERN.search(sentence):
            continue

        # Một câu có thể chứa nhiều hành động nối bởi dấu phẩy hoặc "and".
        for segment in _split_action_sentence(sentence):
            candidate_name = _clean_raw_use_case_segment(segment)
            if not candidate_name:
                continue
            use_cases.append(
                {
                    "name": candidate_name,
                    "complexity": _guess_raw_use_case_complexity(candidate_name),
                }
            )

    return use_cases


def _split_action_sentence(sentence: str) -> list[str]:
    """Tách câu thành các action segment nhỏ hơn."""
    action_text = normalize_name(sentence)

    # Xóa phần chủ ngữ hoặc mẫu câu dẫn nhập để còn lại động từ chức năng.
    # Ví dụ:
    # "The Customer can browse products and place order"
    # -> "browse products and place order"
    cleanup_patterns = [
        r"^The system allows (?:the |a |an )?[A-Za-z\s-]+ to ",
        r"^The system lets (?:the |a |an )?[A-Za-z\s-]+ to ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ can ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ may ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ must ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ should ",
        r"^(?:The |A |An )?[A-Za-z\s-]+ will ",
    ]

    for pattern in cleanup_patterns:
        action_text = re.sub(pattern, "", action_text, flags=re.IGNORECASE)

    return [segment.strip() for segment in re.split(r",| and | or ", action_text) if segment.strip()]


def _clean_raw_use_case_segment(segment: str) -> str:
    """Làm sạch raw use case segment trước khi đưa sang normalization."""
    cleaned_segment = normalize_name(segment)

    # Loại bỏ các từ nối khiến tên use case không còn gọn.
    cleaned_segment = re.sub(r"^(to)\s+", "", cleaned_segment, flags=re.IGNORECASE)
    cleaned_segment = re.sub(r"\b(after|before|when|if)\b.*$", "", cleaned_segment, flags=re.IGNORECASE)
    cleaned_segment = cleaned_segment.strip(" .,:;")

    if not cleaned_segment:
        return ""

    if not _contains_action_verb(cleaned_segment):
        return ""

    return cleaned_segment


def _contains_action_verb(segment: str) -> bool:
    """Kiểm tra segment có chứa action verb hay không."""
    lowered_segment = segment.lower()
    if any(re.search(rf"\b{re.escape(verb)}\b", lowered_segment) for verb in ACTION_VERB_PATTERNS):
        return True

    return any(re.search(rf"\b{re.escape(phrase)}\b", lowered_segment) for phrase in VERB_CANONICAL_MAP)


def _guess_raw_use_case_complexity(name: str) -> str:
    """Ước lượng complexity thô ở layer 1.

    Layer 2 sẽ chuẩn hóa lại complexity nên hàm này chỉ cần rule đơn giản.
    """
    lowered_name = name.lower()

    # Đây chỉ là complexity "đoán nhanh" ở layer 1.
    # Kết quả cuối cùng vẫn do normalization classifier quyết định.
    # Nhóm simple:
    # đây là các use case tra cứu/hiển thị, ít bước, nên được đoán nhanh là simple.
    if any(keyword in lowered_name for keyword in ["login", "log in", "search", "lookup", "view", "browse", "check", "display"]):
        return "simple"
    # Nhóm complex:
    # bao gồm cả các transactional workflow mới của banking như transfer/send money.
    # Rule complex phải đứng trước average để tránh bị phân loại sai.
    if any(
        keyword in lowered_name
        for keyword in [
            "transfer money",
            "transfer funds",
            "transfer payment",
            "send money",
            "transfer",
            "book",
            "reserve",
            "borrow",
            "place order",
            "checkout",
            "enroll",
            "schedule",
            "manage",
        ]
    ):
        return "complex"
    # Nhóm average:
    # thường là tạo/cập nhật/xác nhận/thanh toán ở mức xử lý trung bình.
    if any(keyword in lowered_name for keyword in ["register", "create", "submit", "return", "confirm", "approve", "payment", "pay", "update"]):
        return "average"
    return "average"


def _build_notes(mode: str, file_name: str | None, source_text: str) -> list[str]:
    """Tạo ghi chú ngắn để frontend hiển thị trạng thái extraction."""
    notes = []

    if mode == "mock":
        notes.append("Đang dùng mock extraction với pipeline 3 lớp cho free-text input.")
    else:
        notes.append("Đang dùng placeholder LLM mode: đã build prompt và giữ sẵn vị trí để nối LLM API thật trong tương lai.")

    if file_name:
        notes.append(f"Đã đọc nội dung text từ file upload '{file_name}'.")

    if _looks_like_use_case_template(source_text):
        notes.append("Đầu vào được nhận diện là Use Case Document theo template có các field như Use Case ID, Primary Actor, Main Flow và Postconditions.")

    notes.append("Kết quả đã qua normalization để bỏ 'System', gộp trùng, merge sub-action và giữ domain noun.")
    return notes


def _looks_like_use_case_template(text: str) -> bool:
    """Kiểm tra text có giống Use Case Document theo template hay không."""
    lowered_text = text.lower()
    required_markers = (
        "use case id",
        "use case name",
        "primary actor",
        "main flow",
    )
    return all(marker in lowered_text for marker in required_markers)


def _extract_template_payload(text: str) -> dict[str, list[dict[str, str]]]:
    """Trích xuất actor và use case từ Use Case Document có cấu trúc template."""
    actor_map: dict[str, dict[str, str]] = {}
    use_cases: list[dict[str, str]] = []

    # Mỗi block "Use Case X" sẽ được đọc độc lập.
    # Cách làm này giúp:
    # - lấy đúng Use Case Name
    # - lấy đúng Primary Actor / Secondary Actor
    # - ước lượng complexity từ Main Flow / Alternative Flow
    for block in USE_CASE_BLOCK_PATTERN.findall(text):
        parsed_block = _parse_template_use_case_block(block)
        if parsed_block is None:
            continue

        use_case_name = parsed_block["name"]
        description = parsed_block["description"]
        complexity = parsed_block["complexity"]

        use_cases.append(
            {
                "name": use_case_name,
                "complexity": complexity,
                "description": description,
            }
        )

        for actor_name in parsed_block["actors"]:
            actor_map.setdefault(
                actor_name.lower(),
                {"name": actor_name, "complexity": "average"},
            )

    return {
        "actors": list(actor_map.values()),
        "use_cases": use_cases,
    }


def _parse_template_use_case_block(block: str) -> dict[str, object] | None:
    """Phân tích một block Use Case trong tài liệu template."""
    lines = [normalize_name(line) for line in block.splitlines() if normalize_name(line)]
    if not lines:
        return None

    header_line = lines[0]
    header_name = header_line.split(":", 1)[1].strip() if ":" in header_line else header_line
    sections: dict[str, str] = {}
    index = 1

    # Vòng lặp này đọc từng nhãn section trong template như:
    # Use Case Name, Primary Actor, Description, Main Flow...
    while index < len(lines):
        current_line = lines[index]

        if current_line not in TEMPLATE_SECTION_LABELS:
            index += 1
            continue

        label = current_line
        index += 1
        collected_lines: list[str] = []

        while index < len(lines) and lines[index] not in TEMPLATE_SECTION_LABELS:
            collected_lines.append(lines[index])
            index += 1

        sections[label] = "\n".join(collected_lines).strip()

    use_case_name = sections.get("Use Case Name") or header_name
    description = sections.get("Description", "")
    actors = _split_actor_names(
        sections.get("Primary Actor", ""),
        sections.get("Secondary Actor", ""),
    )
    complexity = _estimate_template_use_case_complexity(
        use_case_name=use_case_name,
        main_flow_text=sections.get("Main Flow", ""),
        alternative_flow_text=sections.get("Alternative Flow", ""),
    )

    if not use_case_name:
        return None

    return {
        "name": use_case_name,
        "description": description or None,
        "actors": actors,
        "complexity": complexity,
    }


def _split_actor_names(*actor_fields: str) -> list[str]:
    """Tách danh sách actor từ các field Primary Actor / Secondary Actor."""
    actor_names: list[str] = []

    for field_value in actor_fields:
        if not field_value:
            continue

        parts = re.split(r",| and | & ", field_value, flags=re.IGNORECASE)
        for part in parts:
            actor_name = normalize_name(part)
            if actor_name:
                actor_names.append(actor_name)

    return actor_names


def _estimate_template_use_case_complexity(
    use_case_name: str,
    main_flow_text: str,
    alternative_flow_text: str,
) -> str:
    """Ước lượng complexity từ cấu trúc flow của template."""
    lowered_name = use_case_name.lower()
    main_steps = _count_flow_steps(main_flow_text)
    alternative_steps = _count_flow_steps(alternative_flow_text)

    # Ưu tiên 1:
    # transactional workflow luôn được xếp complex.
    # Rule này bao phủ cả domain banking như Transfer Money / Send Money.
    if any(
        lowered_name.startswith(keyword)
        for keyword in (
            "transfer",
            "send money",
            "book",
            "reserve",
            "borrow",
            "place order",
            "checkout",
            "enroll",
            "schedule",
            "manage",
        )
    ):
        return "complex"

    # Ưu tiên 2:
    # các action xử lý mức trung bình như register/confirm/pay/update.
    if any(
        lowered_name.startswith(keyword)
        for keyword in ("register", "create", "submit", "confirm", "approve", "return", "payment", "pay", "update")
    ):
        return "average"

    # Ưu tiên 3:
    # nhóm tra cứu/hiển thị luôn simple, kể cả có alternative flow kiểu "không có kết quả".
    if any(
        lowered_name.startswith(keyword)
        for keyword in ("login", "log in", "search", "view", "browse", "check", "display", "lookup", "look up")
    ):
        # Nhóm tra cứu/hiển thị luôn được xem là simple theo rule mới,
        # dù tài liệu template có thêm Alternative Flow mô tả "không có kết quả".
        return "simple"

    # Nếu tên use case không rơi vào rule keyword ở trên,
    # thì fallback sang số bước trong flow của template.
    if main_steps >= 8 or alternative_steps >= 2:
        return "complex"

    if (main_steps + alternative_steps) >= 4 or alternative_steps >= 1:
        return "average"

    return "simple"


def _count_flow_steps(flow_text: str) -> int:
    """Đếm số bước trong Main Flow hoặc Alternative Flow."""
    if not flow_text.strip():
        return 0

    lines = [normalize_name(line) for line in flow_text.splitlines() if normalize_name(line)]
    return len(lines)
