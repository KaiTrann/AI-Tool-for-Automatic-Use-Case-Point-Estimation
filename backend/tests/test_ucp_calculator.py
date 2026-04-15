"""Bộ test đơn giản cho luồng tính toán UCP.

Các test được viết ngắn gọn để sinh viên dễ đọc và dễ giải thích khi báo cáo.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.request_models import Actor, UseCase
from app.services.effort_estimation_service import estimate_effort
from app.services.schedule_estimation_service import estimate_schedule
from app.services.ucp_calculator import (
    UCPError,
    calculate_actor_weight,
    calculate_effort_estimation,
    calculate_uaw,
    calculate_uucp,
    calculate_ucp,
    calculate_use_case_weight,
    calculate_uucw,
)

client = TestClient(app)


def test_actor_weight_calculation() -> None:
    """Test 1: kiểm tra trọng số của actor theo mức độ phức tạp."""
    assert calculate_actor_weight("simple") == 1
    assert calculate_actor_weight("average") == 2
    assert calculate_actor_weight("complex") == 3


def test_use_case_weight_calculation() -> None:
    """Test 2: kiểm tra trọng số của use case theo mức độ phức tạp."""
    assert calculate_use_case_weight("simple") == 5
    assert calculate_use_case_weight("average") == 10
    assert calculate_use_case_weight("complex") == 15


def test_uaw_calculation() -> None:
    """Test 3: UAW phải bằng tổng trọng số của các actor."""
    actors = [
        Actor(name="User", complexity="simple"),
        Actor(name="Admin", complexity="complex"),
        Actor(name="Manager", complexity="average"),
    ]

    assert calculate_uaw(actors) == 6.0


def test_uucw_calculation() -> None:
    """Test 4: UUCW phải bằng tổng trọng số của các use case."""
    use_cases = [
        UseCase(name="Login", complexity="simple"),
        UseCase(name="Manage Users", complexity="average"),
        UseCase(name="Generate Report", complexity="complex"),
    ]

    assert calculate_uucw(use_cases) == 30.0


def test_uucp_calculation() -> None:
    """Test 5: UUCP phải bằng UAW + UUCW."""
    assert calculate_uucp(6.0, 30.0) == 36.0


def test_ucp_calculation() -> None:
    """Test 6: UCP phải bằng UUCP nhân với TCF và ECF."""
    assert calculate_ucp(36.0, 1.1, 0.9) == 35.64


def test_effort_calculation() -> None:
    """Test 7: effort phải bằng UCP nhân với productivity factor."""
    assert calculate_effort_estimation(35.64, 20) == 712.8

    effort = estimate_effort(35.64, 20)
    assert effort.hours == 712.8
    assert effort.person_days == 89.1


def test_schedule_calculation() -> None:
    """Test 8: schedule phải được tính từ effort hours và team size."""
    schedule = estimate_schedule(hours=712.8, team_size=3)

    assert schedule.months == 1.48
    assert schedule.recommended_team_size == 3
    assert schedule.sprint_count == 3


def test_invalid_complexity_values() -> None:
    """Test 9: giá trị complexity sai phải sinh lỗi rõ ràng."""
    with pytest.raises(UCPError):
        calculate_actor_weight("expert")

    with pytest.raises(UCPError):
        calculate_use_case_weight("expert")


def test_ucp_calculate_endpoint() -> None:
    """Test 10: API /ucp/calculate phải trả về kết quả đúng."""
    response = client.post(
        "/ucp/calculate",
        json={
            "actors": [
                {"name": "User", "complexity": "simple"},
                {"name": "Admin", "complexity": "complex"},
                {"name": "Manager", "complexity": "average"},
            ],
            "use_cases": [
                {"name": "Login", "complexity": "simple"},
                {"name": "Manage Users", "complexity": "average"},
                {"name": "Generate Report", "complexity": "complex"},
            ],
            "technical_complexity_factor": 1.1,
            "environmental_complexity_factor": 0.9,
            "productivity_factor": 20,
            "team_size": 3,
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["ucp"]["uaw"] == 9.0
    assert payload["ucp"]["uucw"] == 30.0
    assert payload["ucp"]["uucp"] == 39.0
    assert payload["ucp"]["ucp"] == 38.61
    assert payload["effort"]["hours"] == 772.2
    assert payload["schedule"]["months"] == 1.61


def test_exact_ecommerce_sample_metrics() -> None:
    """E-commerce sample phải cho ra đúng UAW, UUCW và UCP."""
    actors = [
        Actor(name="Customer", complexity="complex"),
        Actor(name="Administrator", complexity="complex"),
        Actor(name="Payment Gateway", complexity="simple"),
    ]
    use_cases = [
        UseCase(name="Register", complexity="average"),
        UseCase(name="Login", complexity="simple"),
        UseCase(name="Browse Products", complexity="simple"),
        UseCase(name="Search Products", complexity="simple"),
        UseCase(name="Add To Cart", complexity="average"),
        UseCase(name="Place Order", complexity="complex"),
        UseCase(name="Make Payment", complexity="average"),
        UseCase(name="Manage Products", complexity="complex"),
        UseCase(name="Confirm Orders", complexity="average"),
        UseCase(name="Generate Reports", complexity="average"),
    ]

    uaw = calculate_uaw(actors)
    uucw = calculate_uucw(use_cases)
    uucp = calculate_uucp(uaw, uucw)
    ucp = calculate_ucp(uucp, 1.0, 1.0)

    assert uaw == 7.0
    assert uucw == 95.0
    assert uucp == 102.0
    assert ucp == 102.0


def test_exact_library_sample_metrics() -> None:
    """Library sample phải cho ra đúng UAW, UUCW và UCP."""
    actors = [
        Actor(name="Reader", complexity="complex"),
        Actor(name="Librarian", complexity="complex"),
        Actor(name="Email Service", complexity="simple"),
        Actor(name="Reporting Service", complexity="simple"),
    ]
    use_cases = [
        UseCase(name="Register", complexity="average"),
        UseCase(name="Login", complexity="simple"),
        UseCase(name="Browse Books", complexity="simple"),
        UseCase(name="Search Books", complexity="simple"),
        UseCase(name="View Book Details", complexity="simple"),
        UseCase(name="Borrow Books", complexity="complex"),
        UseCase(name="Reserve Books", complexity="complex"),
        UseCase(name="Return Books", complexity="average"),
        UseCase(name="Manage Book Information", complexity="complex"),
        UseCase(name="Manage Members", complexity="complex"),
        UseCase(name="Generate Reports", complexity="average"),
    ]

    uaw = calculate_uaw(actors)
    uucw = calculate_uucw(use_cases)
    uucp = calculate_uucp(uaw, uucw)
    ucp = calculate_ucp(uucp, 1.0, 1.0)

    assert uaw == 8.0
    assert uucw == 110.0
    assert uucp == 118.0
    assert ucp == 118.0
