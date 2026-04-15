"""Module tính toán UCP cốt lõi.

Module này chỉ làm một việc:
- nhận actor và use case đã có complexity rõ ràng
- áp công thức UCP

Việc trích xuất và normalization nằm ở lớp khác.
Nhờ vậy phần tính toán luôn đơn giản, dễ kiểm thử và dễ giải thích trong báo cáo.
"""

from app.models.request_models import Actor, UCPRequest, UseCase
from app.models.response_models import UCPResponse

ACTOR_WEIGHTS = {
    "simple": 1,
    "average": 2,
    "complex": 3,
}

USE_CASE_WEIGHTS = {
    "simple": 5,
    "average": 10,
    "complex": 15,
}


class UCPError(ValueError):
    """Lỗi nghiệp vụ khi dữ liệu đầu vào của bộ tính UCP không hợp lệ."""


def calculate_actor_weight(complexity: str) -> int:
    """Trả về trọng số của actor theo mức độ phức tạp."""
    try:
        # Map trực tiếp complexity -> weight theo chuẩn đơn giản của đồ án.
        return ACTOR_WEIGHTS[complexity]
    except KeyError as error:
        raise UCPError(
            f"Độ phức tạp của actor '{complexity}' không hợp lệ. Hãy dùng simple, average hoặc complex."
        ) from error


def calculate_use_case_weight(complexity: str) -> int:
    """Trả về trọng số của use case theo mức độ phức tạp."""
    try:
        # Map trực tiếp complexity -> weight theo chuẩn đơn giản của đồ án.
        return USE_CASE_WEIGHTS[complexity]
    except KeyError as error:
        raise UCPError(
            f"Độ phức tạp của use case '{complexity}' không hợp lệ. Hãy dùng simple, average hoặc complex."
        ) from error


def calculate_uaw(actors: list[Actor]) -> float:
    """Tính UAW bằng tổng trọng số của tất cả actor."""
    if not actors:
        raise UCPError("Danh sách actor không được để trống.")
    # Cộng trọng số của từng actor sau khi complexity đã được xác định.
    return float(sum(calculate_actor_weight(actor.complexity) for actor in actors))


def calculate_uucw(use_cases: list[UseCase]) -> float:
    """Tính UUCW bằng tổng trọng số của tất cả use case."""
    if not use_cases:
        raise UCPError("Danh sách use case không được để trống.")
    # Cộng trọng số của từng use case sau khi complexity đã được xác định.
    return float(sum(calculate_use_case_weight(use_case.complexity) for use_case in use_cases))


def calculate_uucp(uaw: float, uucw: float) -> float:
    """Tính UUCP = UAW + UUCW."""
    # UUCP là tổng chưa hiệu chỉnh, chưa nhân TCF và ECF.
    return round(uaw + uucw, 2)


def calculate_ucp(uucp: float, tcf: float, ecf: float) -> float:
    """Tính UCP đã hiệu chỉnh theo TCF và ECF."""
    if tcf <= 0:
        raise UCPError("TCF phải lớn hơn 0.")
    if ecf <= 0:
        raise UCPError("ECF phải lớn hơn 0.")

    # Công thức cốt lõi của UCP:
    # UCP = UUCP * TCF * ECF
    return round(uucp * tcf * ecf, 2)


def calculate_effort_estimation(ucp: float, productivity_factor: float) -> float:
    """Tính effort từ UCP và hệ số năng suất."""
    if productivity_factor <= 0:
        raise UCPError("Hệ số năng suất phải lớn hơn 0.")

    # Effort được giữ theo đơn vị giờ công trong project này.
    return round(ucp * productivity_factor, 2)


def calculate_ucp_metrics(request_data: UCPRequest) -> UCPResponse:
    """Chạy toàn bộ chuỗi công thức UCP và trả về kết quả có cấu trúc."""
    try:
        # Tính lần lượt theo đúng thứ tự công thức để dễ kiểm tra và dễ giải thích.
        uaw = calculate_uaw(request_data.actors)
        uucw = calculate_uucw(request_data.use_cases)
        uucp = calculate_uucp(uaw, uucw)
        ucp = calculate_ucp(uucp, request_data.tcf, request_data.ecf)
        effort_estimation = calculate_effort_estimation(ucp, request_data.productivity_factor)
    except (TypeError, ValueError) as error:
        raise UCPError(str(error)) from error

    return UCPResponse(
        uaw=uaw,
        uucw=uucw,
        uucp=uucp,
        ucp=ucp,
        effort_estimation=effort_estimation,
    )
