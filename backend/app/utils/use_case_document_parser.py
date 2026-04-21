"""Parser rule-based cho nhiều mẫu SRS / Use Case Document.

Mục tiêu của parser:
- hỗ trợ cả template cũ và template IEEE/SRS mới
- không phụ thuộc cứng vào số section như 2.4.5 hay 5.4
- nhận diện bằng nhãn section/field
- chuẩn hóa mọi tài liệu về cùng một schema nội bộ trước khi tính UCP
"""

from __future__ import annotations

import re

from app.models.requests import NormalizedUseCaseDocument
from app.utils.actor_normalizer import normalize_actor_list
from app.utils.field_aliases import (
    FIELD_ALIASES,
    IGNORED_SECTION_PATTERNS,
    INLINE_METADATA_FIELDS,
    SECTION_ALIASES,
)
from app.utils.parser import normalize_name
from app.utils.use_case_extractor import extract_use_case_name

PRIMARY_ACTOR_ALIASES = ("primary actor",)
SECONDARY_ACTOR_ALIASES = ("secondary actor", "secondary actors", "supporting actors", "other actors")
USE_CASE_ID_PATTERN = re.compile(r"\bUC(?:[.\s-]?[A-Z0-9]+)+\b", re.IGNORECASE)
UC_BLOCK_HEADER_PATTERN = re.compile(
    r"^\s*(?:UC(?:[.\s-]?[A-Z0-9]+)+\s*:.*|UC(?:[.\s-]?[A-Z0-9]+)+\s+[^\s].*|Use Case\s+\d+\s*:.*)$",
    re.IGNORECASE,
)
STEP_PREFIX_PATTERN = re.compile(r"^\s*(?:\d+[\.\)]|[A-Za-z][\.\)]|[-*•])\s*")


def looks_like_use_case_document(text: str) -> bool:
    """Kiểm tra input có giống tài liệu SRS / use case document hay không."""
    lowered_text = text.lower()

    matched_field_count = sum(
        1
        for aliases in FIELD_ALIASES.values()
        if any(alias in lowered_text for alias in aliases)
    )
    has_section_hint = any(
        any(alias in lowered_text for alias in aliases)
        for aliases in SECTION_ALIASES.values()
    )
    has_uc_marker = USE_CASE_ID_PATTERN.search(text) is not None or UC_BLOCK_HEADER_PATTERN.search(text) is not None

    return matched_field_count >= 3 and (has_section_hint or has_uc_marker)


def parse_use_case_documents(text: str) -> list[NormalizedUseCaseDocument]:
    """Parse tài liệu về danh sách use case theo schema chuẩn nội bộ."""
    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Bước 1:
    # đọc trước bảng List of Use Case để lấy index cấp cao.
    listed_documents = _parse_use_case_list_section(normalized_text)

    # Bước 2:
    # parse các block specification chi tiết.
    relevant_text = _slice_relevant_use_case_content(normalized_text)
    detailed_blocks = _split_use_case_blocks(relevant_text)
    detailed_documents = [
        parsed_document
        for block in detailed_blocks
        if (parsed_document := _parse_use_case_block(block)) is not None
    ]

    # Bước 3:
    # merge dữ liệu list/index với block chi tiết để tạo schema thống nhất.
    return _merge_listed_and_detailed_documents(listed_documents, detailed_documents)


def _parse_use_case_list_section(text: str) -> list[NormalizedUseCaseDocument]:
    """Parse section 'List of Use Case' thành index use case cấp cao."""
    lines = text.splitlines()
    documents: list[NormalizedUseCaseDocument] = []

    for start_index in _find_section_start_indexes(lines, "list_of_use_case"):
        section_lines = _collect_section_lines(lines, start_index)
        documents.extend(_parse_use_case_list_lines(section_lines))

    return _deduplicate_documents(documents)


def _parse_use_case_list_lines(section_lines: list[str]) -> list[NormalizedUseCaseDocument]:
    """Parse các dòng trong section List of Use Case theo nhiều layout khác nhau."""
    documents: list[NormalizedUseCaseDocument] = []
    lowered_section_lines = [normalize_name(line).lower() for line in section_lines if normalize_name(line)]
    has_table_headers = all(
        header in lowered_section_lines
        for header in ("use case id", "use case name")
    )
    if not has_table_headers:
        has_table_headers = any(
            "use case id" in line and "use case name" in line
            for line in lowered_section_lines
        )

    # Layout 1:
    # một dòng chứa đầy đủ ID | Name | FR.
    if has_table_headers:
        for line in section_lines:
            if not USE_CASE_ID_PATTERN.search(line):
                continue
            if _is_ignored_line(line) or _looks_like_toc_row(line):
                continue

            parsed_document = _parse_use_case_list_row(line)
            if parsed_document is not None:
                documents.append(parsed_document)

    if documents:
        return documents

    # Layout 2:
    # bảng bị bung thành từng dòng riêng:
    # UC.01
    # Manage Employee Records
    # FR1
    if not has_table_headers:
        return []

    cleaned_lines = [
        normalize_name(line)
        for line in section_lines
        if normalize_name(line) and not _is_ignored_line(line)
    ]
    cleaned_lines = [
        line
        for line in cleaned_lines
        if line.lower() not in {"<liệt kê các use case>", "use case id", "use case name", "functional req.", "functional req"}
    ]

    index = 0
    while index < len(cleaned_lines):
        current_line = cleaned_lines[index]
        if USE_CASE_ID_PATTERN.fullmatch(current_line) is None:
            index += 1
            continue

        use_case_id = _normalize_use_case_id(current_line)
        use_case_name = cleaned_lines[index + 1] if index + 1 < len(cleaned_lines) else None
        functional_requirement = cleaned_lines[index + 2] if index + 2 < len(cleaned_lines) else None

        normalized_name = extract_use_case_name(use_case_name, None)
        if normalized_name:
            documents.append(
                NormalizedUseCaseDocument(
                    use_case_id=use_case_id,
                    use_case_name=normalized_name,
                    functional_requirement=functional_requirement,
                    source_template_type="use_case_list",
                )
            )
            index += 3
            continue

        index += 1

    return documents


def _parse_use_case_list_row(line: str) -> NormalizedUseCaseDocument | None:
    """Parse một dòng trong bảng/danh sách use case."""
    cleaned_line = normalize_name(line)
    id_match = USE_CASE_ID_PATTERN.search(cleaned_line)
    if id_match is None:
        return None

    use_case_id = _normalize_use_case_id(id_match.group(0))
    trailing_text = cleaned_line[id_match.end() :].strip(" .:-|\t")
    if not trailing_text:
        return None

    cells = _split_row_cells(trailing_text)
    if not cells:
        return None

    use_case_name = cells[0]
    functional_requirement = cells[1] if len(cells) > 1 else None

    normalized_name = extract_use_case_name(use_case_name, None)
    if not normalized_name:
        return None

    return NormalizedUseCaseDocument(
        use_case_id=use_case_id,
        use_case_name=normalized_name,
        functional_requirement=functional_requirement,
        source_template_type="use_case_list",
    )


def _slice_relevant_use_case_content(text: str) -> str:
    """Cắt phần tài liệu có khả năng chứa use case specification thật."""
    lines = text.splitlines()

    for start_index in _find_section_start_indexes(lines, "use_case_specification"):
        if not _looks_like_toc_row(lines[start_index]):
            return "\n".join(lines[start_index:])

    for index in range(len(lines)):
        if _is_valid_block_start(lines, index):
            return "\n".join(lines[index:])

    return text


def _split_use_case_blocks(text: str) -> list[str]:
    """Tách tài liệu thành từng block use case độc lập."""
    lines = text.splitlines()
    block_starts = [
        index
        for index in range(len(lines))
        if _is_valid_block_start(lines, index)
    ]
    if not block_starts:
        return []

    blocks: list[str] = []
    for position, start_index in enumerate(block_starts):
        end_index = block_starts[position + 1] if position + 1 < len(block_starts) else len(lines)
        block_text = "\n".join(lines[start_index:end_index]).strip()
        if block_text:
            blocks.append(block_text)

    return blocks


def _parse_use_case_block(block: str) -> NormalizedUseCaseDocument | None:
    """Parse một block specification thành schema chuẩn nội bộ."""
    lines = [line.strip() for line in block.splitlines() if line.strip()]
    if not lines:
        return None

    header_line = lines[0] if _is_header_style_block_start(lines[0]) else None
    content_lines = lines[1:] if header_line else lines

    sections: dict[str, list[str]] = {}
    current_field: str | None = None

    for line in content_lines:
        if _is_ignored_line(line):
            # Khi gặp metadata như "Created by" hoặc "Date Created",
            # cần ngắt field hiện tại để value ở dòng sau không bị dính vào
            # field trước đó như Use Case Name.
            current_field = None
            continue

        matched_field, inline_value = _match_field_label(line)
        if matched_field is not None:
            current_field = matched_field
            sections.setdefault(current_field, [])
            if inline_value:
                sections[current_field].append(inline_value)
            continue

        if current_field is None:
            continue

        sections.setdefault(current_field, []).append(line)

    structured_field_count = sum(
        1
        for field_name in ("use_case_id", "use_case_name", "actors", "description", "main_flow")
        if sections.get(field_name)
    )
    if structured_field_count < 2:
        return None

    explicit_name = _join_field_text(sections.get("use_case_name"))
    use_case_name = extract_use_case_name(explicit_name, header_line)
    if not use_case_name:
        return None

    raw_actor_lines: list[str] = []
    raw_actor_lines.extend(sections.get("actors", []))
    raw_actor_lines.extend(sections.get("primary_actor", []))
    raw_actor_lines.extend(sections.get("secondary_actors", []))

    # Không ghép toàn bộ actor lines thành một chuỗi duy nhất trước khi tách,
    # vì như vậy "Guest" + "Payment Gateway" sẽ bị dính thành một actor sai.
    parsed_actors: list[str] = []
    for actor_line in raw_actor_lines:
        parsed_actors.extend(normalize_actor_list(actor_line))
    parsed_actors = _deduplicate_strings(parsed_actors)

    primary_actor_candidates = normalize_actor_list(_join_field_text(sections.get("primary_actor")))
    secondary_actor_candidates = normalize_actor_list(_join_field_text(sections.get("secondary_actors")))

    primary_actor = primary_actor_candidates[0] if primary_actor_candidates else (parsed_actors[0] if parsed_actors else None)
    secondary_actors = secondary_actor_candidates

    if not secondary_actors and parsed_actors:
        secondary_actors = [actor_name for actor_name in parsed_actors if actor_name != primary_actor]

    use_case_id = _join_field_text(sections.get("use_case_id")) or _extract_use_case_id_from_header(header_line)
    template_type = _detect_template_type_from_block(block)
    main_flow_steps = _parse_step_lines(sections.get("main_flow", []))
    alternative_flow_steps = _parse_step_lines(sections.get("alternative_flows", []))
    exception_flow_steps = _parse_step_lines(sections.get("exception_flows", []))

    all_actors = _deduplicate_strings(
        [actor_name for actor_name in [primary_actor, *secondary_actors, *parsed_actors] if actor_name]
    )

    return NormalizedUseCaseDocument(
        use_case_id=_normalize_use_case_id(use_case_id) if use_case_id else None,
        use_case_name=use_case_name,
        actors=all_actors,
        primary_actor=primary_actor,
        secondary_actors=_deduplicate_strings(secondary_actors),
        description=_join_field_text(sections.get("description")),
        goal=_join_field_text(sections.get("goal")),
        trigger=_join_field_text(sections.get("trigger")),
        preconditions=_join_field_text(sections.get("preconditions")),
        postconditions=_join_field_text(sections.get("postconditions")),
        main_flow_steps=main_flow_steps,
        alternative_flow_steps=alternative_flow_steps,
        exception_flow_steps=exception_flow_steps,
        main_success_scenario=main_flow_steps,
        alternative_flows=alternative_flow_steps,
        exception_flows=exception_flow_steps,
        priority=_join_field_text(sections.get("priority")),
        business_rules=_join_field_text(sections.get("business_rules")),
        notes=_join_field_text(sections.get("notes")),
        source_template_type=template_type,
    )


def _find_section_start_indexes(lines: list[str], section_key: str) -> list[int]:
    """Tìm vị trí bắt đầu của một section dựa trên alias text."""
    section_aliases = SECTION_ALIASES[section_key]
    return [
        index
        for index, line in enumerate(lines)
        if any(alias in normalize_name(line).lower() for alias in section_aliases)
    ]


def _collect_section_lines(lines: list[str], start_index: int) -> list[str]:
    """Thu các dòng của một section cho đến trước section lớn kế tiếp."""
    collected_lines: list[str] = []

    for index in range(start_index + 1, len(lines)):
        normalized_line = normalize_name(lines[index]).lower()
        if not normalized_line:
            continue

        if _looks_like_section_heading(normalized_line):
            break

        # Nếu gặp heading lớn mới kiểu "6. Something" thì dừng để tránh ăn lố section.
        if re.match(r"^\d+(?:\.\d+)*\s+[A-Za-z]", normalize_name(lines[index])):
            break

        collected_lines.append(lines[index])

    return collected_lines


def _looks_like_section_heading(normalized_line: str) -> bool:
    """Kiểm tra một dòng có giống heading section lớn hay không."""
    for aliases in SECTION_ALIASES.values():
        for alias in aliases:
            if normalized_line == alias:
                return True
            if normalized_line.startswith(alias) and "|" not in normalized_line:
                return True
            if re.match(rf"^\d+(?:\.\d+)*\s+{re.escape(alias)}$", normalized_line):
                return True
    return False


def _split_row_cells(value: str) -> list[str]:
    """Tách một dòng bảng thành các cell text."""
    if "|" in value:
        return [normalize_name(cell) for cell in value.split("|") if normalize_name(cell)]

    cells = [normalize_name(cell) for cell in re.split(r"\t+|\s{2,}", value) if normalize_name(cell)]
    if cells:
        return cells

    return [normalize_name(value)] if normalize_name(value) else []


def _match_field_label(line: str) -> tuple[str | None, str | None]:
    """Kiểm tra một dòng có phải field label hợp lệ hay không."""
    normalized_line = normalize_name(line)
    lowered_line = normalized_line.lower()

    for alias in PRIMARY_ACTOR_ALIASES:
        if lowered_line == alias:
            return "primary_actor", None
        if lowered_line.startswith(f"{alias}:"):
            return "primary_actor", normalize_name(normalized_line.split(":", 1)[1])

    for alias in SECONDARY_ACTOR_ALIASES:
        if lowered_line == alias:
            return "secondary_actors", None
        if lowered_line.startswith(f"{alias}:"):
            return "secondary_actors", normalize_name(normalized_line.split(":", 1)[1])

    for canonical_field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if lowered_line == alias:
                return canonical_field, None
            if lowered_line.startswith(f"{alias}:"):
                return canonical_field, normalize_name(normalized_line.split(":", 1)[1])

    return None, None


def _extract_use_case_id_from_header(header_line: str | None) -> str | None:
    """Lấy use case id từ header UC.xx nếu có."""
    if not header_line:
        return None

    match = USE_CASE_ID_PATTERN.search(normalize_name(header_line))
    if match is None:
        return None

    return _normalize_use_case_id(match.group(0))


def _normalize_use_case_id(value: str | None) -> str | None:
    """Chuẩn hóa ID use case để merge các nguồn dữ liệu dễ hơn."""
    if not value:
        return None

    cleaned_value = normalize_name(value).upper().replace(" ", ".")
    cleaned_value = cleaned_value.replace("..", ".")
    return cleaned_value


def _parse_step_lines(lines: list[str]) -> list[str]:
    """Làm sạch danh sách step trong main/alternative/exception flow."""
    steps: list[str] = []
    current_step_parts: list[str] = []
    has_numbered_steps = False

    for line in lines:
        if _is_ignored_line(line):
            continue

        cleaned_line = normalize_name(line).strip(" -:*")
        if not cleaned_line:
            continue

        if cleaned_line.lower() in {"step", "actor action", "system response"}:
            continue

        if re.fullmatch(r"\d+", cleaned_line):
            has_numbered_steps = True
            if current_step_parts:
                steps.append(" / ".join(current_step_parts))
                current_step_parts = []
            continue

        if re.match(
            r"^(luồng phụ|luồng ngoại lệ|alternative flow|alternative scenario|exception flow|exception)\b",
            cleaned_line,
            flags=re.IGNORECASE,
        ):
            if current_step_parts:
                steps.append(" / ".join(current_step_parts))
                current_step_parts = []
            continue

        cleaned_line = STEP_PREFIX_PATTERN.sub("", cleaned_line).strip(" -:*")
        if not cleaned_line:
            continue

        if has_numbered_steps:
            current_step_parts.append(cleaned_line)
        else:
            steps.append(cleaned_line)

    if current_step_parts:
        steps.append(" / ".join(current_step_parts))

    return steps


def _join_field_text(lines: list[str] | None) -> str | None:
    """Ghép nhiều dòng thành một chuỗi sạch."""
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
    """Loại các dòng metadata / heading / caption không phải business content."""
    lowered_line = normalize_name(line).lower()
    if not lowered_line:
        return True

    if any(pattern in lowered_line for pattern in IGNORED_SECTION_PATTERNS):
        return True

    if any(lowered_line == field_name or lowered_line.startswith(f"{field_name}:") for field_name in INLINE_METADATA_FIELDS):
        return True

    if re.search(r"^(figure|fig\.|diagram|image)\b", lowered_line):
        return True

    if _looks_like_toc_row(lowered_line):
        return True

    return False


def _looks_like_toc_row(line: str) -> bool:
    """Nhận diện dòng kiểu mục lục."""
    return re.search(r"\.{3,}\s*\d+$", line) is not None


def _is_valid_block_start(lines: list[str], index: int) -> bool:
    """Kiểm tra một dòng có thật sự là đầu block use case hay không."""
    line = normalize_name(lines[index])
    if not line or _is_ignored_line(line):
        return False

    if _is_header_style_block_start(line):
        lookahead_markers = _count_structure_markers(lines, index)
        return lookahead_markers >= 3

    matched_field, _ = _match_field_label(line)
    if matched_field == "use_case_id":
        lookahead_markers = _count_structure_markers(lines, index)
        return lookahead_markers >= 3

    return False


def _is_header_style_block_start(line: str) -> bool:
    """Kiểm tra header dạng UC.xx: Name."""
    normalized_line = normalize_name(line)
    if any(alias in normalized_line.lower() for alias in SECTION_ALIASES["use_case_specification"]):
        return False
    return UC_BLOCK_HEADER_PATTERN.match(normalized_line) is not None


def _count_structure_markers(lines: list[str], start_index: int) -> int:
    """Đếm số field marker hợp lệ quanh một block."""
    lookahead_window = [
        normalize_name(candidate_line).lower()
        for candidate_line in lines[start_index : min(start_index + 20, len(lines))]
        if normalize_name(candidate_line)
    ]

    required_markers = (
        "use case id",
        "use case name",
        "actors",
        "actor",
        "brief description",
        "description",
        "main flow",
        "main success scenario",
        "trigger",
    )
    return sum(
        1
        for marker in required_markers
        if any(candidate_line == marker or candidate_line.startswith(f"{marker}:") for candidate_line in lookahead_window)
    )


def _detect_template_type_from_block(block: str) -> str:
    """Đoán loại template để ghi chú nguồn dữ liệu."""
    lowered_block = block.lower()
    if "brief description" in lowered_block and "business rule" in lowered_block:
        return "ieee_srs"
    if "main success scenario" in lowered_block or "primary actor" in lowered_block:
        return "legacy_srs"
    return "structured_srs"


def _merge_listed_and_detailed_documents(
    listed_documents: list[NormalizedUseCaseDocument],
    detailed_documents: list[NormalizedUseCaseDocument],
) -> list[NormalizedUseCaseDocument]:
    """Merge dữ liệu list/index và specification chi tiết về một danh sách duy nhất."""
    merged_map: dict[str, NormalizedUseCaseDocument] = {}
    ordered_keys: list[str] = []

    for document in listed_documents + detailed_documents:
        document_key = _document_key(document)
        if document_key not in merged_map:
            merged_map[document_key] = document
            ordered_keys.append(document_key)
            continue

        merged_map[document_key] = _merge_two_documents(merged_map[document_key], document)

    return [merged_map[key] for key in ordered_keys]


def _merge_two_documents(
    base_document: NormalizedUseCaseDocument,
    overlay_document: NormalizedUseCaseDocument,
) -> NormalizedUseCaseDocument:
    """Merge hai document cùng một use case, ưu tiên dữ liệu chi tiết hơn."""
    merged_actors = _deduplicate_strings([*base_document.actors, *overlay_document.actors])
    merged_secondary_actors = _deduplicate_strings(
        [*base_document.secondary_actors, *overlay_document.secondary_actors]
    )

    return NormalizedUseCaseDocument(
        use_case_id=overlay_document.use_case_id or base_document.use_case_id,
        use_case_name=overlay_document.use_case_name or base_document.use_case_name,
        actors=merged_actors,
        primary_actor=overlay_document.primary_actor or base_document.primary_actor,
        secondary_actors=merged_secondary_actors,
        description=overlay_document.description or base_document.description,
        goal=overlay_document.goal or base_document.goal,
        trigger=overlay_document.trigger or base_document.trigger,
        preconditions=overlay_document.preconditions or base_document.preconditions,
        postconditions=overlay_document.postconditions or base_document.postconditions,
        functional_requirement=overlay_document.functional_requirement or base_document.functional_requirement,
        main_flow_steps=overlay_document.main_flow_steps or base_document.main_flow_steps,
        alternative_flow_steps=overlay_document.alternative_flow_steps or base_document.alternative_flow_steps,
        exception_flow_steps=overlay_document.exception_flow_steps or base_document.exception_flow_steps,
        main_success_scenario=overlay_document.main_success_scenario or base_document.main_success_scenario,
        alternative_flows=overlay_document.alternative_flows or base_document.alternative_flows,
        exception_flows=overlay_document.exception_flows or base_document.exception_flows,
        priority=overlay_document.priority or base_document.priority,
        business_rules=overlay_document.business_rules or base_document.business_rules,
        source_template_type=overlay_document.source_template_type or base_document.source_template_type,
        notes=overlay_document.notes or base_document.notes,
    )


def _document_key(document: NormalizedUseCaseDocument) -> str:
    """Tạo key ổn định để merge use case cùng ID hoặc cùng tên."""
    if document.use_case_id:
        return f"id::{document.use_case_id.lower()}"
    return f"name::{document.use_case_name.lower()}"


def _deduplicate_documents(documents: list[NormalizedUseCaseDocument]) -> list[NormalizedUseCaseDocument]:
    """Loại trùng tài liệu theo ID/tên nhưng giữ thứ tự."""
    seen: set[str] = set()
    unique_documents: list[NormalizedUseCaseDocument] = []

    for document in documents:
        document_key = _document_key(document)
        if document_key in seen:
            continue
        seen.add(document_key)
        unique_documents.append(document)

    return unique_documents


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
