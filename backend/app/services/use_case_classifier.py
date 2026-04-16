"""Phân loại use case theo số transaction trong Use Case Specification.

Nguyên tắc chuẩn UCP dùng trong project:
- simple: <= 3 transaction
- average: 4 đến 7 transaction
- complex: > 7 transaction

Quan trọng:
- với tài liệu có cấu trúc, số transaction là nguồn quyết định chính
- keyword chỉ là fallback khi không parse được flow chuẩn
"""

from __future__ import annotations

from app.models.requests import NormalizedUseCaseDocument

# Fallback keyword heuristic chỉ dùng khi không có tài liệu flow có cấu trúc.
# Đây không phải nguồn quyết định chính với SRS / Use Case Specification chuẩn.
FALLBACK_SIMPLE_KEYWORDS = ("login", "search", "view", "browse", "check", "display", "lookup")
FALLBACK_AVERAGE_KEYWORDS = ("register", "create", "submit", "confirm", "approve", "return", "pay", "update")
FALLBACK_COMPLEX_KEYWORDS = ("book", "reserve", "borrow", "enroll", "place order", "transfer", "manage", "checkout")


def count_transactions_from_main_flow(
    use_case_document: NormalizedUseCaseDocument,
    include_alt: bool = False,
) -> int:
    """Đếm transaction từ flow của use case.

    Trong prototype này, mỗi bước có ý nghĩa trong flow được xem là
    một transaction candidate. Cách làm này đơn giản, dễ giải thích,
    và đủ phù hợp cho đồ án sinh viên.
    """
    # Mỗi bước có ý nghĩa trong Main Success Scenario được xem là
    # một transaction candidate trong phạm vi đồ án này.
    transaction_count = len(_filter_meaningful_steps(use_case_document.main_success_scenario))

    if include_alt:
        # Khi cần nghiên cứu sâu hơn, có thể cộng cả flow phụ và flow ngoại lệ.
        transaction_count += len(_filter_meaningful_steps(use_case_document.alternative_flows))
        transaction_count += len(_filter_meaningful_steps(use_case_document.exception_flows))

    return transaction_count


def classify_use_case_by_transaction_count(transaction_count: int) -> str:
    """Phân loại use case theo chuẩn UCP dựa trên số transaction."""
    # Rule chuẩn UCP cho project này:
    # - <= 3: simple
    # - 4 đến 7: average
    # - > 7: complex
    if transaction_count <= 3:
        return "simple"
    if transaction_count <= 7:
        return "average"
    return "complex"


def classify_use_case_document(
    use_case_document: NormalizedUseCaseDocument,
    include_alt: bool = False,
) -> tuple[str, int]:
    """Phân loại use case ưu tiên theo flow có cấu trúc, fallback sang heuristic."""
    transaction_count = count_transactions_from_main_flow(use_case_document, include_alt=include_alt)

    # Nếu đếm được transaction từ tài liệu,
    # đây là nguồn dữ liệu chính để xác định complexity.
    if transaction_count > 0:
        return classify_use_case_by_transaction_count(transaction_count), transaction_count

    # Nếu không parse được flow có cấu trúc, mới fallback sang heuristic nhẹ.
    return classify_use_case_by_name_fallback(use_case_document.use_case_name), 0


def classify_use_case_by_name_fallback(use_case_name: str) -> str:
    """Fallback nhẹ theo keyword khi input không phải Use Case Specification rõ ràng."""
    lowered_name = use_case_name.lower()

    if any(lowered_name.startswith(keyword) for keyword in FALLBACK_COMPLEX_KEYWORDS):
        return "complex"
    if any(lowered_name.startswith(keyword) for keyword in FALLBACK_AVERAGE_KEYWORDS):
        return "average"
    if any(lowered_name.startswith(keyword) for keyword in FALLBACK_SIMPLE_KEYWORDS):
        return "simple"
    return "average"


def _filter_meaningful_steps(steps: list[str]) -> list[str]:
    """Giữ lại các bước có ý nghĩa để tính transaction."""
    meaningful_steps: list[str] = []

    for step in steps:
        cleaned_step = " ".join(step.split()).strip()
        if not cleaned_step:
            continue
        lowered_step = cleaned_step.lower()
        # Loại metadata rác nếu chẳng may lọt vào flow.
        if lowered_step in {
            "create by",
            "created by",
            "last updated by",
            "date created",
            "date last updated",
        }:
            continue
        # Loại caption hình/diagram vì không phải transaction.
        if lowered_step.startswith(("figure ", "fig. ", "diagram ", "image ")):
            continue
        meaningful_steps.append(cleaned_step)

    return meaningful_steps
