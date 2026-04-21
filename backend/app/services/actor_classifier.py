"""Phân loại actor theo rule chuẩn UCP.

Ưu tiên của file này:
1. dùng loại tương tác và ngữ cảnh actor
2. chỉ dùng keyword như một lớp fallback

Chuẩn UCP dùng trong project:
- simple actor: hệ thống ngoài có API rõ ràng
- average actor: file/database/protocol/text-based interface
- complex actor: con người thao tác qua GUI
"""

from __future__ import annotations

import re

from app.models.requests import NormalizedUseCaseDocument
from app.utils.parser import normalize_name

HUMAN_ROLE_KEYWORDS = (
    # Nhóm vai trò con người.
    # Các actor này theo chuẩn UCP sẽ được xem là complex.
    "customer",
    "user",
    "reader",
    "member",
    "librarian",
    "stocker",
    "reading management staff",
    "waiter",
    "barista",
    "cashier",
    "management",
    "guest",
    "manager",
    "administrator",
    "admin",
    "student",
    "teacher",
    "doctor",
    "patient",
    "staff",
    "employee",
    "officer",
    "clerk",
    "hr manager",
    "payroll manager",
    "department manager",
    "line manager",
)

SIMPLE_INTERFACE_KEYWORDS = (
    # Nhóm actor hệ thống ngoài có interface/API rõ ràng.
    # Theo chuẩn UCP sẽ được xếp simple.
    "api",
    "rest",
    "soap",
    "gateway",
    "service",
    "provider",
    "external system",
    "third-party system",
    "web service",
)

AVERAGE_INTERFACE_KEYWORDS = (
    # Nhóm actor tương tác qua file / database / protocol / text.
    # Theo chuẩn UCP sẽ được xếp average.
    "database",
    "db",
    "file",
    "text",
    "csv",
    "excel",
    "spreadsheet",
    "protocol",
    "message",
    "email",
)


def classify_actor(
    actor_name: str,
    role: str = "secondary",
    use_case_document: NormalizedUseCaseDocument | None = None,
) -> str:
    """Phân loại actor theo chuẩn UCP.

    Rule chính:
    - human tương tác GUI -> complex
    - external system có API rõ ràng -> simple
    - file/database/protocol/text-based -> average

    Vì tài liệu use case hiếm khi ghi rõ "GUI/API/file-based",
    hàm này dùng cả context của tài liệu để suy luận một cách ổn định.
    """
    cleaned_name = normalize_name(actor_name)
    lowered_name = cleaned_name.lower()
    context_text = _build_actor_context_text(use_case_document).lower()

    # Ưu tiên 1:
    # nếu actor hoặc ngữ cảnh thể hiện đây là external system qua API/service/gateway
    # thì xếp simple.
    if _contains_any(lowered_name, SIMPLE_INTERFACE_KEYWORDS) or _contains_any(context_text, SIMPLE_INTERFACE_KEYWORDS):
        return "simple"

    # Ưu tiên 2:
    # nếu actor thiên về database/file/protocol/text interface
    # thì xếp average.
    if _contains_any(lowered_name, AVERAGE_INTERFACE_KEYWORDS) or _contains_any(context_text, AVERAGE_INTERFACE_KEYWORDS):
        return "average"

    # Ưu tiên 3:
    # nếu tên actor giống vai trò con người thì xếp complex.
    if _contains_any(lowered_name, HUMAN_ROLE_KEYWORDS):
        return "complex"

    # Nếu actor là primary actor trong use case document,
    # mặc định xem đây là tác nhân chính thao tác qua giao diện.
    if role == "primary":
        return "complex"

    # Các actor dạng "System" trong template IEEE/SRS mới
    # được giữ lại như actor hệ thống thay vì loại bỏ.
    # Ở đây mình xếp chúng về nhánh system actor đơn giản.
    if re.search(r"\b(system|application|platform)\b", lowered_name):
        return "simple"

    # Secondary actor chưa rõ loại thì:
    # - nếu tên giống hệ thống ngoài -> simple
    # - nếu không rõ thì average để an toàn hơn là mặc định complex
    return "average"


def collect_classified_actors(use_case_documents: list[NormalizedUseCaseDocument]) -> list[tuple[str, str]]:
    """Thu thập actor đã được phân loại từ danh sách use case document."""
    actor_map: dict[str, tuple[str, str]] = {}

    for document in use_case_documents:
        # Nếu parser mới đã gom toàn bộ actor vào document.actors,
        # dùng danh sách này làm nguồn bao quát nhất.
        if document.actors:
            for actor_name in document.actors:
                actor_role = "primary" if actor_name == document.primary_actor else "secondary"
                actor_map.setdefault(
                    actor_name.lower(),
                    (actor_name, classify_actor(actor_name, role=actor_role, use_case_document=document)),
                )

        # Primary actor thường là người khởi tạo use case,
        # nên được classify với role="primary".
        if document.primary_actor:
            actor_map.setdefault(
                document.primary_actor.lower(),
                (document.primary_actor, classify_actor(document.primary_actor, role="primary", use_case_document=document)),
            )

        # Secondary actor có thể là người hoặc hệ thống phụ trợ,
        # nên vẫn cần classify theo ngữ cảnh từng use case.
        for secondary_actor in document.secondary_actors:
            actor_map.setdefault(
                secondary_actor.lower(),
                (secondary_actor, classify_actor(secondary_actor, role="secondary", use_case_document=document)),
            )

    return list(actor_map.values())


def _build_actor_context_text(use_case_document: NormalizedUseCaseDocument | None) -> str:
    """Ghép text ngữ cảnh để suy luận kiểu actor."""
    if use_case_document is None:
        return ""

    parts = [
        use_case_document.description or "",
        use_case_document.goal or "",
        use_case_document.trigger or "",
        use_case_document.functional_requirement or "",
        use_case_document.notes or "",
        use_case_document.business_rules or "",
    ]
    return " ".join(part for part in parts if part).strip()


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    """Kiểm tra text có chứa một keyword nào không."""
    return any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in keywords)
