"""Parser rule-based cho SRS / Use Case Specification.

Mục tiêu của parser này:
- chỉ parse block use case thật
- bỏ qua TOC, metadata, danh sách use case, caption hình
- ưu tiên field có cấu trúc hơn text tự do
- hoạt động ổn định với tài liệu SRS dùng template gần chuẩn
"""

from __future__ import annotations

import re

from app.models.requests import NormalizedUseCaseDocument
from app.utils.actor_normalizer import normalize_actor_list
from app.utils.parser import normalize_name
from app.utils.use_case_extractor import extract_use_case_name

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    # Mỗi key là tên field chuẩn nội bộ.
    # Tuple đi kèm là các cách ghi field có thể gặp trong SRS thật.
    "use_case_id": ("use case id", "id"),
    "use_case_name": ("use case name",),
    "primary_actor": ("primary actor", "actor", "actors"),
    "secondary_actors": ("secondary actor", "secondary actors", "supporting actors", "other actors"),
    "description": ("description", "brief description"),
    "trigger": ("trigger",),
    "preconditions": ("pre-condition", "preconditions", "precondition"),
    "postconditions": ("post-condition", "postconditions", "postcondition"),
    "main_success_scenario": ("main success scenario", "main flow", "basic flow", "normal flow"),
    "alternative_flows": ("alternative scenario", "alternative scenarios", "alternative flow", "alternative flows"),
    "exception_flows": ("exception", "exceptions", "exception flow", "exception flows"),
    "priority": ("priority",),
    "business_rules": ("business rule", "business rules"),
    "notes": ("notes", "note", "goal"),
}

IGNORED_FIELD_LABELS = (
    # Các field metadata cần bỏ hoàn toàn,
    # không được coi là nội dung business của use case.
    "create by",
    "created by",
    "last updated by",
    "date created",
    "date last updated",
)

IGNORED_SECTION_PATTERNS = (
    # Các section cấp tài liệu cần bỏ qua vì không phải block use case thật.
    r"table of contents",
    r"revision history",
    r"introduction",
    r"project overview",
    r"high level functional requirement",
    r"high level fucntional requirement",
    r"stakeholders",
    r"list of use cases",
)

USE_CASE_SPEC_SECTION_PATTERN = re.compile(r"\b2\.(?:4|5)\.5\b.*use case specification", re.IGNORECASE)
UC_BLOCK_HEADER_PATTERN = re.compile(
    r"^\s*(?:UC[\.\s]?\d+\s*:.*|UC[\.\s]?\d+\s+[A-Za-z].*|Use Case\s+\d+\s*:.*)$",
    re.IGNORECASE | re.MULTILINE,
)
STEP_PREFIX_PATTERN = re.compile(r"^\s*(?:\d+[\.\)]|[A-Za-z][\.\)]|[-*•])\s*")


def looks_like_use_case_document(text: str) -> bool:
    """Kiểm tra tài liệu có phải SRS / Use Case Specification hay không."""
    lowered_text = text.lower()
    matched_labels = sum(
        1
        for aliases in FIELD_ALIASES.values()
        if any(alias in lowered_text for alias in aliases)
    )

    # Một tài liệu được xem là Use Case Document nếu:
    # - có vài field label đặc trưng
    # - và có section Use Case Specification hoặc có block UC.xx
    return matched_labels >= 3 and (
        USE_CASE_SPEC_SECTION_PATTERN.search(text) is not None
        or UC_BLOCK_HEADER_PATTERN.search(text) is not None
    )


def parse_use_case_documents(text: str) -> list[NormalizedUseCaseDocument]:
    """Parse tài liệu thành danh sách use case theo schema chuẩn nội bộ."""
    # Bước 1:
    # cắt bỏ phần đầu tài liệu không liên quan như TOC hoặc overview.
    relevant_text = _slice_relevant_use_case_content(text)
    # Bước 2:
    # tách phần còn lại thành từng block UC độc lập.
    blocks = _split_use_case_blocks(relevant_text)
    documents: list[NormalizedUseCaseDocument] = []

    for block in blocks:
        # Bước 3:
        # parse từng block về schema chuẩn nội bộ.
        parsed_document = _parse_use_case_block(block)
        if parsed_document is not None:
            documents.append(parsed_document)

    return documents


def _slice_relevant_use_case_content(text: str) -> str:
    """Chỉ giữ phần nội dung liên quan đến Use Case Specification."""
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized_text.splitlines()

    for index, line in enumerate(lines):
        if USE_CASE_SPEC_SECTION_PATTERN.search(line) and not _looks_like_toc_row(line):
            # Không dừng ngay ở TOC row kiểu "2.5.5 Use Case Specification25".
            # Chỉ chấp nhận nếu các dòng phía sau thật sự có field của use case.
            lookahead_lines = "\n".join(lines[index : min(index + 20, len(lines))]).lower()
            if "use case id" in lookahead_lines and (
                "actors" in lookahead_lines or "use case name" in lookahead_lines
            ):
                return "\n".join(lines[index:])

    first_block_match = UC_BLOCK_HEADER_PATTERN.search(normalized_text)
    if first_block_match:
        return normalized_text[first_block_match.start():]

    return normalized_text


def _split_use_case_blocks(text: str) -> list[str]:
    """Tách tài liệu thành từng UC block độc lập."""
    lines = [line for line in text.splitlines()]
    if not any(line.strip() for line in lines):
        return []

    # Tìm tất cả vị trí có khả năng là đầu block UC.
    block_start_indexes = [
        index
        for index in range(len(lines))
        if _is_valid_block_header(lines, index)
    ]
    if not block_start_indexes:
        return []

    blocks: list[str] = []
    for position, start_index in enumerate(block_start_indexes):
        # Mỗi block kéo dài đến trước block UC kế tiếp.
        end_index = block_start_indexes[position + 1] if position + 1 < len(block_start_indexes) else len(lines)
        block_text = "\n".join(lines[start_index:end_index]).strip()
        if block_text:
            blocks.append(block_text)

    return blocks


def _parse_use_case_block(block: str) -> NormalizedUseCaseDocument | None:
    """Parse một UC block và bỏ qua block rác như TOC/list row."""
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return None

    header_line = lines[0]
    sections: dict[str, list[str]] = {}
    current_field: str | None = None

    for line in lines[1:]:
        if _is_ignored_line(line):
            current_field = None
            continue

        # Nếu dòng hiện tại là label field như "Use Case Name" hay "Trigger"
        # thì chuyển context sang field đó.
        canonical_field, inline_value = _match_field_label(line)
        if canonical_field is not None:
            current_field = canonical_field
            sections.setdefault(current_field, [])
            if inline_value:
                sections[current_field].append(inline_value)
            continue

        if current_field is None:
            continue

        # Nếu đang đứng trong một field hợp lệ
        # thì gắn dòng hiện tại vào field đó.
        sections.setdefault(current_field, []).append(line)

    # Block hợp lệ phải có ít nhất vài field nghiệp vụ thực sự,
    # nếu không thì rất có thể đó chỉ là TOC row hoặc list of use cases row.
    structured_field_count = sum(
        1
        for field_name in (
            "use_case_name",
            "primary_actor",
            "description",
            "trigger",
            "preconditions",
            "postconditions",
            "main_success_scenario",
        )
        if sections.get(field_name)
    )
    if structured_field_count < 2:
        return None

    use_case_name = extract_use_case_name(
        explicit_name=_join_field_text(sections.get("use_case_name")),
        header_line=header_line,
    )
    if not use_case_name:
        return None

    actor_candidates = normalize_actor_list(_join_field_text(sections.get("primary_actor")))
    secondary_actors = normalize_actor_list(_join_field_text(sections.get("secondary_actors")))

    # Nếu field Actors chứa nhiều actor trên cùng một chỗ:
    # - actor đầu làm primary
    # - phần còn lại làm secondary
    primary_actor = actor_candidates[0] if actor_candidates else None
    if len(actor_candidates) > 1:
        secondary_actors = actor_candidates[1:] + secondary_actors

    header_use_case_id = _extract_use_case_id_from_header(header_line)

    return NormalizedUseCaseDocument(
        use_case_id=_join_field_text(sections.get("use_case_id")) or header_use_case_id,
        use_case_name=use_case_name,
        primary_actor=primary_actor,
        secondary_actors=_deduplicate_strings(secondary_actors),
        description=_join_field_text(sections.get("description")),
        trigger=_join_field_text(sections.get("trigger")),
        preconditions=_join_field_text(sections.get("preconditions")),
        postconditions=_join_field_text(sections.get("postconditions")),
        main_success_scenario=_parse_step_lines(sections.get("main_success_scenario", [])),
        alternative_flows=_parse_step_lines(sections.get("alternative_flows", [])),
        exception_flows=_parse_step_lines(sections.get("exception_flows", [])),
        priority=_join_field_text(sections.get("priority")),
        business_rules=_join_field_text(sections.get("business_rules")),
        notes=_join_field_text(sections.get("notes")),
    )


def _match_field_label(line: str) -> tuple[str | None, str | None]:
    """Kiểm tra một dòng có phải field hợp lệ của use case block hay không."""
    normalized_line = normalize_name(line)
    lowered_line = normalized_line.lower()

    for canonical_field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if lowered_line == alias:
                return canonical_field, None
            if lowered_line.startswith(f"{alias}:"):
                return canonical_field, normalize_name(normalized_line.split(":", 1)[1])

    return None, None


def _extract_use_case_id_from_header(header_line: str) -> str | None:
    """Lấy use case id từ UC header."""
    match = re.match(r"^\s*(UC[\.\s]?\d+)", normalize_name(header_line), flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).upper().replace(" ", ".")


def _parse_step_lines(lines: list[str]) -> list[str]:
    """Làm sạch danh sách step và loại dòng rác."""
    steps: list[str] = []
    current_step_parts: list[str] = []
    has_numbered_steps = False

    for line in lines:
        if _is_ignored_line(line):
            continue

        cleaned_line = normalize_name(line)
        cleaned_line = cleaned_line.strip(" -:*")
        if not cleaned_line:
            continue

        # Bỏ các header cột trong bảng flow.
        if cleaned_line.lower() in {"step", "actor action", "system response"}:
            continue

        # Nếu gặp dòng chỉ chứa số thứ tự bước,
        # bắt đầu gom nội dung cho một step mới.
        if re.fullmatch(r"\d+", cleaned_line):
            has_numbered_steps = True
            if current_step_parts:
                steps.append(" / ".join(current_step_parts))
                current_step_parts = []
            continue

        # Nếu gặp tiêu đề flow phụ / flow ngoại lệ,
        # đóng step đang gom và chuyển sang chờ bước mới.
        if re.match(r"^(luồng phụ|luồng ngoại lệ|alternative flow|alternative scenario|exception flow|exception)\b", cleaned_line, flags=re.IGNORECASE):
            if current_step_parts:
                steps.append(" / ".join(current_step_parts))
                current_step_parts = []
            continue

        cleaned_line = STEP_PREFIX_PATTERN.sub("", cleaned_line).strip(" -:*")
        if not cleaned_line:
            continue

        # Với tài liệu dạng bảng Step / Actor Action / System Response,
        # một step có thể gồm nhiều dòng. Ta ghép chúng bằng " / ".
        if has_numbered_steps:
            current_step_parts.append(cleaned_line)
        else:
            steps.append(cleaned_line)

    if current_step_parts:
        steps.append(" / ".join(current_step_parts))

    return steps


def _join_field_text(lines: list[str] | None) -> str | None:
    """Ghép text nhiều dòng thành một chuỗi sạch."""
    if not lines:
        return None

    cleaned_lines = [
        normalize_name(line)
        for line in lines
        if normalize_name(line) and not _is_ignored_line(line)
    ]
    if not cleaned_lines:
        return None

    return "\n".join(cleaned_lines)


def _is_ignored_line(line: str) -> bool:
    """Loại các dòng không thuộc business content của use case."""
    lowered_line = normalize_name(line).lower()
    if not lowered_line:
        return True

    # Loại các section cấp tài liệu không phải nội dung của use case.
    if any(re.search(pattern, lowered_line) for pattern in IGNORED_SECTION_PATTERNS):
        return True

    # Loại metadata field riêng lẻ.
    if lowered_line in IGNORED_FIELD_LABELS:
        return True

    # Loại metadata field nếu ghi kiểu inline "Created by: ...".
    if any(lowered_line.startswith(f"{label}:") for label in IGNORED_FIELD_LABELS):
        return True

    # Loại caption hình/diagram.
    if re.search(r"^(figure|fig\.|diagram|image)\b", lowered_line):
        return True

    # Dòng kiểu TOC có chấm dẫn trang cũng bị bỏ.
    if _looks_like_toc_row(lowered_line):
        return True

    return False


def _looks_like_toc_row(line: str) -> bool:
    """Nhận diện dòng kiểu Table of Contents."""
    return re.search(r"\.{3,}\s*\d+$", line) is not None


def _is_valid_block_header(lines: list[str], index: int) -> bool:
    """Kiểm tra một dòng UC có thật sự là đầu block specification hay không."""
    line = lines[index].strip()
    if not line:
        return False

    if UC_BLOCK_HEADER_PATTERN.match(line) is None:
        return False

    previous_non_empty_line = ""
    for previous_index in range(index - 1, -1, -1):
        if lines[previous_index].strip():
            previous_non_empty_line = normalize_name(lines[previous_index]).lower()
            break

    # Nếu ngay trước đó là field "Use Case ID" thì đây chỉ là value của field, không phải block header.
    if previous_non_empty_line == "use case id":
        return False

    # Nhìn các dòng phía sau để xem đây có thật sự là block use case hay chỉ là TOC/list row.
    lookahead_window = [
        normalize_name(candidate_line).lower()
        for candidate_line in lines[index : min(index + 20, len(lines))]
        if normalize_name(candidate_line)
    ]

    required_markers = (
        "use case id",
        "use case name",
        "actors",
        "actor",
        "brief description",
        "description",
        "trigger",
        "main flow",
        "pre-conditions",
        "preconditions",
    )
    marker_count = sum(
        1
        for marker in required_markers
        if any(
            candidate_line == marker or candidate_line.startswith(f"{marker}:")
            for candidate_line in lookahead_window
        )
    )

    # Chỉ chấp nhận header nếu xung quanh có đủ vài marker đặc trưng của use case thật.
    return marker_count >= 4


def _deduplicate_strings(values: list[str]) -> list[str]:
    """Loại trùng nhưng giữ nguyên thứ tự."""
    seen: set[str] = set()
    unique_values: list[str] = []

    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_values.append(value)

    return unique_values
