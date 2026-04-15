"""Bộ test API cơ bản cho backend."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ECOMMERCE_TEXT = """
The system allows a Customer to register and log in.
The Customer can browse products, search for products, add products to the shopping cart, place an order, and make payment.
After a successful order, the system sends a confirmation.

The Administrator can log in, manage products, update stock, confirm customer orders, and generate reports.

An external Payment Gateway is used to process online payments.
"""

LIBRARY_TEXT = """
The Reader can register, login, browse books, search books, view book details, borrow books, reserve books, and return books.
The Librarian can manage book information, manage members, and generate reports.
An Email Service sends overdue reminders.
A Reporting Service integrates with the library platform.
"""

HOSPITAL_TEXT = """
The Patient can register, login, schedule appointments, view medical records, and pay bills.
The Doctor can review patient records and approve prescriptions.
The Receptionist can manage appointments.
An Email Service sends appointment reminders.
"""

HOTEL_TEXT = """
The Guest can register, login, search rooms, view room details, book room, and make payment.
The Receptionist can confirm bookings and manage reservations.
A Payment Gateway processes online payments.
An Email Service sends booking reminders.
"""

HOTEL_REFINED_TEXT = """
The Guest can register, login, search rooms, view room details, check booking status, book rooms, reserve rooms, and pay online.
The Receptionist can confirm bookings.
The Hotel Manager can update room availability, delete room information, manage reservations, and approve discounts.
A Payment Gateway processes online payments.
An Email Service sends booking reminders.
"""

EDUCATION_TEXT = """
The Student can register, login, search courses, view course materials, submit assignments, book appointments, and reserve lab equipment.
The Instructor can create assignments and approve grades.
The Education Manager can manage courses, manage students, manage instructors, manage assignments, and manage class schedules.
An Email Service is used to send notifications.
A Reporting Service integrates with the education platform.
"""


def test_health() -> None:
    """API health phải luôn trả về trạng thái hoạt động."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_extract() -> None:
    """API extract phải trả về actor và use case."""
    response = client.post(
        "/extract",
        data={
            "text": "The student submits requirements. The admin reviews the report.",
            "llm_mode": "mock",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["actors"]) >= 1
    assert len(payload["use_cases"]) >= 1


def test_extract_with_uploaded_plain_text_file() -> None:
    """API extract phải đọc được uploaded text file đơn giản."""
    response = client.post(
        "/extract",
        data={"text": "", "llm_mode": "mock"},
        files={"uploaded_file": ("requirements.txt", LIBRARY_TEXT.encode("utf-8"), "text/plain")},
    )

    assert response.status_code == 200
    payload = response.json()
    actor_names = [actor["name"] for actor in payload["actors"]]
    use_case_names = [use_case["name"] for use_case in payload["use_cases"]]
    assert "Reader" in actor_names
    assert "Search Books" in use_case_names


def test_extract_with_mock_docx_upload_content() -> None:
    """API extract phải xử lý được mock uploaded content với tên file .docx."""
    response = client.post(
        "/extract",
        data={"text": "", "llm_mode": "placeholder"},
        files={
            "uploaded_file": (
                "requirements.docx",
                HOTEL_TEXT.encode("utf-8"),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    actor_names = [actor["name"] for actor in payload["actors"]]
    use_case_names = [use_case["name"] for use_case in payload["use_cases"]]
    assert "Guest" in actor_names
    assert "Book Room" in use_case_names


def test_ucp_calculate() -> None:
    """API tính UCP phải trả về các giá trị cơ bản chính xác."""
    response = client.post(
        "/ucp/calculate",
        json={
            "actors": [
                {"name": "User", "complexity": "simple"},
                {"name": "Admin", "complexity": "complex"},
            ],
            "use_cases": [
                {"name": "Submit requirements", "complexity": "simple"},
                {"name": "Generate report", "complexity": "complex"},
            ],
            "technical_complexity_factor": 1.1,
            "environmental_complexity_factor": 0.9,
            "productivity_factor": 20,
            "team_size": 3,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ucp"]["uaw"] == 6.0
    assert payload["ucp"]["uucw"] == 20.0
    assert payload["ucp"]["ucp"] == 25.74


def test_analyze_and_calculate_returns_expected_ecommerce_metrics() -> None:
    """E-commerce phải trả đúng metrics UCP."""
    response = client.post(
        "/analyze-and-calculate",
        data={
            "text": ECOMMERCE_TEXT,
            "llm_mode": "placeholder",
            "technical_complexity_factor": "1.0",
            "environmental_complexity_factor": "1.0",
            "productivity_factor": "20",
            "team_size": "3",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["ucp"]["uaw"] == 7.0
    assert payload["ucp"]["uucw"] == 95.0
    assert payload["ucp"]["uucp"] == 102.0
    assert payload["ucp"]["ucp"] == 102.0


def test_analyze_and_calculate_returns_expected_library_metrics() -> None:
    """Library system phải trả đúng metrics UCP."""
    response = client.post(
        "/analyze-and-calculate",
        data={
            "text": LIBRARY_TEXT,
            "llm_mode": "placeholder",
            "technical_complexity_factor": "1.0",
            "environmental_complexity_factor": "1.0",
            "productivity_factor": "20",
            "team_size": "3",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["ucp"]["uaw"] == 8.0
    assert payload["ucp"]["uucw"] == 110.0
    assert payload["ucp"]["uucp"] == 118.0
    assert payload["ucp"]["ucp"] == 118.0


def test_extract_supports_hospital_domain() -> None:
    """Hospital domain mới phải extract được actor và use case hợp lý."""
    response = client.post(
        "/extract",
        data={
            "text": HOSPITAL_TEXT,
            "llm_mode": "placeholder",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    actor_names = [actor["name"] for actor in payload["actors"]]
    use_case_names = [use_case["name"] for use_case in payload["use_cases"]]
    assert "Patient" in actor_names
    assert "Doctor" in actor_names
    assert "Schedule Appointments" in use_case_names


def test_extract_supports_hotel_domain() -> None:
    """Hotel booking domain mới phải extract được actor và use case hợp lý."""
    response = client.post(
        "/extract",
        data={
            "text": HOTEL_TEXT,
            "llm_mode": "placeholder",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    actor_names = [actor["name"] for actor in payload["actors"]]
    use_case_names = [use_case["name"] for use_case in payload["use_cases"]]
    assert "Guest" in actor_names
    assert "Book Room" in use_case_names


def test_analyze_and_calculate_returns_expected_hotel_metrics() -> None:
    """Hotel system phải trả đúng metrics UCP sau normalization."""
    response = client.post(
        "/analyze-and-calculate",
        data={
            "text": HOTEL_REFINED_TEXT,
            "llm_mode": "placeholder",
            "technical_complexity_factor": "1.0",
            "environmental_complexity_factor": "1.0",
            "productivity_factor": "20",
            "team_size": "3",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["ucp"]["uaw"] == 11.0
    assert payload["ucp"]["uucw"] == 120.0
    assert payload["ucp"]["uucp"] == 131.0
    assert payload["ucp"]["ucp"] == 131.0


def test_analyze_and_calculate_returns_expected_education_metrics() -> None:
    """Education system phải trả đúng metrics UCP sau normalization."""
    response = client.post(
        "/analyze-and-calculate",
        data={
            "text": EDUCATION_TEXT,
            "llm_mode": "placeholder",
            "technical_complexity_factor": "1.0",
            "environmental_complexity_factor": "1.0",
            "productivity_factor": "20",
            "team_size": "3",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["ucp"]["uaw"] == 11.0
    assert payload["ucp"]["uucw"] == 160.0
    assert payload["ucp"]["uucp"] == 171.0
    assert payload["ucp"]["ucp"] == 171.0
