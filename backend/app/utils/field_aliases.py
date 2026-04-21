"""Khai báo alias field/section cho nhiều template SRS / Use Case Document.

File này tách riêng các alias để parser:
- không bị phụ thuộc vào một template cũ duy nhất
- dễ mở rộng khi thêm template IEEE/SRS mới
- dễ bảo trì hơn so với việc hard-code label trong parser
"""

from __future__ import annotations

SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    # Các section lớn ở cấp tài liệu.
    "list_of_use_case": (
        "list of use case",
        "list of use cases",
        "use case list",
    ),
    "use_case_specification": (
        "use case specification",
        "use-case specification",
        "use case specs",
    ),
    "functional_requirements": (
        "functional requirements",
        "functional requirement",
        "high level functional requirement",
        "high level fucntional requirement",
    ),
}

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    # Mỗi key là tên field chuẩn nội bộ.
    # Tuple đi kèm là những nhãn có thể gặp trong các template cũ/mới.
    "use_case_id": (
        "use case id",
        "id",
    ),
    "use_case_name": (
        "use case name",
        "name",
    ),
    "actors": (
        "actors",
        "actor",
        "primary actor",
        "secondary actor",
        "secondary actors",
        "supporting actors",
        "other actors",
    ),
    "description": (
        "brief description",
        "description",
    ),
    "goal": (
        "goal",
        "objective",
        "site",
    ),
    "trigger": (
        "trigger",
    ),
    "preconditions": (
        "pre-condition",
        "pre-conditions",
        "precondition",
        "preconditions",
    ),
    "postconditions": (
        "post-condition",
        "post-conditions",
        "postcondition",
        "postconditions",
    ),
    "main_flow": (
        "main flow",
        "main success scenario",
        "basic flow",
        "normal flow",
    ),
    "alternative_flows": (
        "alternative flow",
        "alternative flows",
        "alternative scenario",
        "alternative scenarios",
        "alternative yun",
    ),
    "exception_flows": (
        "exception flow",
        "exception flows",
        "exception",
        "exceptions",
        "exception stream",
    ),
    "priority": (
        "priority",
    ),
    "business_rules": (
        "business rule",
        "business rules",
    ),
    "functional_requirement": (
        "functional requirement",
        "functional requirements",
        "fr",
        "req",
    ),
    "notes": (
        "note",
        "notes",
        "created by",
        "last updated by",
        "date created",
        "date last updated",
    ),
}

INLINE_METADATA_FIELDS = (
    "created by",
    "last updated by",
    "date created",
    "date last updated",
)

IGNORED_SECTION_PATTERNS = (
    "table of contents",
    "revision history",
    "introduction",
    "project overview",
    "stakeholders",
    "appendix",
    "figure",
    "diagram",
    "image",
)
