"""Module tính toán UCP cốt lõi.

Module này chỉ làm một việc:
- nhận actor và use case đã có complexity rõ ràng
- áp công thức UCP

Việc trích xuất và normalization nằm ở lớp khác.
Nhờ vậy phần tính toán luôn đơn giản, dễ kiểm thử và dễ giải thích trong báo cáo.
"""

# Model input/output của core calculator.
# Các model này đã được Pydantic validate trước khi tính.
from app.models.request_models import Actor, UCPRequest, UseCase
from app.models.response_models import UCPResponse

# Bảng trọng số actor theo chuẩn UCP:
# - simple actor thường là external system có API rõ ràng
# - average actor thường là interface dạng protocol/file/database/text
# - complex actor thường là human actor dùng GUI
ACTOR_WEIGHTS = {
    "simple": 1,
    "average": 2,
    "complex": 3,
}

# Bảng trọng số use case theo chuẩn UCP:
# - simple: ít transaction
# - average: số transaction trung bình
# - complex: nhiều transaction
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
        # Ví dụ: "complex" -> 3.
        return ACTOR_WEIGHTS[complexity]
    except KeyError as error:
        # Nếu complexity không thuộc simple/average/complex thì báo lỗi rõ ràng.
        # Lỗi này thường xảy ra khi dữ liệu chưa được normalize đúng.
        raise UCPError(
            f"Độ phức tạp của actor '{complexity}' không hợp lệ. Hãy dùng simple, average hoặc complex."
        ) from error


def calculate_use_case_weight(complexity: str) -> int:
    """Trả về trọng số của use case theo mức độ phức tạp."""
    try:
        # Map trực tiếp complexity -> weight theo chuẩn đơn giản của đồ án.
        # Ví dụ: "average" -> 10.
        return USE_CASE_WEIGHTS[complexity]
    except KeyError as error:
        # Nếu complexity sai, dừng tính để tránh UCP bị sai âm thầm.
        raise UCPError(
            f"Độ phức tạp của use case '{complexity}' không hợp lệ. Hãy dùng simple, average hoặc complex."
        ) from error


def calculate_uaw(actors: list[Actor]) -> float:
    """Tính UAW bằng tổng trọng số của tất cả actor."""
    # UAW không có ý nghĩa nếu danh sách actor rỗng,
    # nên hàm chủ động báo lỗi để frontend hiển thị cho người dùng.
    if not actors:
        raise UCPError("Danh sách actor không được để trống.")

    # Cộng trọng số của từng actor sau khi complexity đã được xác định.
    # Ví dụ:
    # Customer complex = 3
    # Payment Gateway simple = 1
    # UAW = 4
    return float(sum(calculate_actor_weight(actor.complexity) for actor in actors))


def calculate_uucw(use_cases: list[UseCase]) -> float:
    """Tính UUCW bằng tổng trọng số của tất cả use case."""
    # UUCW không có ý nghĩa nếu chưa có use case nào.
    if not use_cases:
        raise UCPError("Danh sách use case không được để trống.")

    # Cộng trọng số của từng use case sau khi complexity đã được xác định.
    # Ví dụ:
    # Login simple = 5
    # Place Order complex = 15
    # UUCW = 20
    return float(sum(calculate_use_case_weight(use_case.complexity) for use_case in use_cases))


def calculate_uucp(uaw: float, uucw: float) -> float:
    """Tính UUCP = UAW + UUCW."""
    # UUCP là tổng chưa hiệu chỉnh, chưa nhân TCF và ECF.
    # UUCP = Unadjusted Use Case Points.
    return round(uaw + uucw, 2)


def calculate_ucp(uucp: float, tcf: float, ecf: float) -> float:
    """Tính UCP đã hiệu chỉnh theo TCF và ECF."""
    # TCF là Technical Complexity Factor.
    # Giá trị phải lớn hơn 0 để phép nhân có ý nghĩa.
    if tcf <= 0:
        raise UCPError("TCF phải lớn hơn 0.")

    # ECF là Environmental Complexity Factor.
    # Giá trị phải lớn hơn 0 tương tự TCF.
    if ecf <= 0:
        raise UCPError("ECF phải lớn hơn 0.")

    # Công thức cốt lõi của UCP:
    # UCP = UUCP * TCF * ECF
    return round(uucp * tcf * ecf, 2)


def calculate_effort_estimation(ucp: float, productivity_factor: float) -> float:
    """Tính effort từ UCP và hệ số năng suất."""
    # productivity_factor biểu diễn số giờ công cho mỗi UCP.
    # Ví dụ mặc định: 20 giờ / 1 UCP.
    if productivity_factor <= 0:
        raise UCPError("Hệ số năng suất phải lớn hơn 0.")

    # Effort được giữ theo đơn vị giờ công trong project này.
    # Ví dụ: UCP = 100, productivity_factor = 20 => effort = 2000 giờ.
    return round(ucp * productivity_factor, 2)


def calculate_ucp_metrics(request_data: UCPRequest) -> UCPResponse:
    """Chạy toàn bộ chuỗi công thức UCP và trả về kết quả có cấu trúc."""
    try:
        # Tính lần lượt theo đúng thứ tự công thức để dễ kiểm tra và dễ giải thích.
        # Bước 1: Actor -> UAW.
        uaw = calculate_uaw(request_data.actors)

        # Bước 2: Use Case -> UUCW.
        uucw = calculate_uucw(request_data.use_cases)

        # Bước 3: UAW + UUCW -> UUCP.
        uucp = calculate_uucp(uaw, uucw)

        # Bước 4: UUCP * TCF * ECF -> UCP cuối cùng.
        ucp = calculate_ucp(uucp, request_data.tcf, request_data.ecf)

        # Bước 5: UCP * productivity factor -> effort estimation.
        effort_estimation = calculate_effort_estimation(ucp, request_data.productivity_factor)
    except (TypeError, ValueError) as error:
        # Gom lỗi kiểu dữ liệu và lỗi nghiệp vụ thành UCPError
        # để route API xử lý thống nhất.
        raise UCPError(str(error)) from error

    # Trả về object response chuẩn để API serialize thành JSON.
    return UCPResponse(
        uaw=uaw,
        uucw=uucw,
        uucp=uucp,
        ucp=ucp,
        effort_estimation=effort_estimation,
    )
