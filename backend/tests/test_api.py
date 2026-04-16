"""Bộ test API cơ bản cho backend."""

from io import BytesIO
from zipfile import ZipFile

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

USE_CASE_TEMPLATE_TEXT = """
Use Case Document - Hotel Booking Management System
Use Case 1: Register Account
Use Case ID
UC-01
Use Case Name
Register Account
Primary Actor
Guest
Description
A guest creates a new account in the hotel booking system.
Main Flow
Guest opens the registration page.
Guest enters personal information.
Guest submits the registration form.
System validates the information.
System creates a new account.
System displays a success message.
Alternative Flow
If the email already exists, the system displays an error message.
Postconditions
A new guest account is created.
Use Case 2: Book Room
Use Case ID
UC-03
Use Case Name
Book Room
Primary Actor
Guest
Secondary Actor
Payment Gateway
Description
A guest books an available room and makes an online payment.
Main Flow
Guest selects a room.
System displays booking details.
Guest confirms the reservation.
System redirects payment to the Payment Gateway.
Guest completes the payment.
Payment Gateway returns payment status.
System stores booking information.
System sends a booking confirmation email.
Alternative Flow
If payment fails, the booking is cancelled.
Postconditions
A new reservation is created.
"""

FULL_HOTEL_USE_CASE_TEMPLATE_TEXT = """
Use Case Document - Hotel Booking Management System
Use Case 1: Register Account
Use Case ID
UC-01
Use Case Name
Register Account
Primary Actor
Guest
Description
A guest creates a new account in the hotel booking system.
Preconditions
The guest does not already have an account.
Main Flow
Guest opens the registration page.
Guest enters personal information.
Guest submits the registration form.
System validates the information.
System creates a new account.
System displays a success message.
Alternative Flow
If the email already exists, the system displays an error message.
Postconditions
A new guest account is created.
Use Case 2: Search Rooms
Use Case ID
UC-02
Use Case Name
Search Rooms
Primary Actor
Guest
Description
A guest searches for available rooms based on date, room type, and number of guests.
Preconditions
The system is online.
Main Flow
Guest enters search criteria.
System checks room availability.
System displays a list of available rooms.
Alternative Flow
If no rooms are available, the system displays a message.
Postconditions
The guest sees available room options.
Use Case 3: Book Room
Use Case ID
UC-03
Use Case Name
Book Room
Primary Actor
Guest
Secondary Actor
Payment Gateway
Description
A guest books an available room and makes an online payment.
Preconditions
The guest is logged in.
A room is available.
Main Flow
Guest selects a room.
System displays booking details.
Guest confirms the reservation.
System redirects payment to the Payment Gateway.
Guest completes the payment.
Payment Gateway returns payment status.
System stores booking information.
System sends a booking confirmation email.
Alternative Flow
If payment fails, the booking is cancelled.
If the selected room becomes unavailable, the system shows an error.
Postconditions
A new reservation is created.
Payment is recorded.
Use Case 4: Cancel Reservation
Use Case ID
UC-04
Use Case Name
Cancel Reservation
Primary Actor
Guest
Description
A guest cancels an existing reservation.
Preconditions
The guest has an active reservation.
Main Flow
Guest opens reservation details.
Guest selects cancel reservation.
System asks for confirmation.
Guest confirms cancellation.
System updates reservation status.
System displays a cancellation message.
Alternative Flow
If the reservation cannot be cancelled, the system displays an error.
Postconditions
Reservation status is updated to cancelled.
Use Case 5: Manage Room Information
Use Case ID
UC-05
Use Case Name
Manage Room Information
Primary Actor
Receptionist
Description
The receptionist manages hotel room details and availability.
Preconditions
Receptionist is logged in.
Main Flow
Receptionist opens the room management page.
Receptionist adds, edits, or deletes room information.
Receptionist updates room availability.
System saves changes.
System displays a success message.
Alternative Flow
If room information is invalid, the system displays an error.
Postconditions
Room information is updated.
Use Case 6: Generate Monthly Report
Use Case ID
UC-06
Use Case Name
Generate Monthly Report
Primary Actor
Hotel Manager
Description
The hotel manager generates a monthly business report.
Preconditions
Hotel manager is logged in.
Main Flow
Hotel manager opens the reports page.
Hotel manager selects a month.
System gathers booking and revenue data.
System generates the report.
System displays the report.
Postconditions
A monthly report is generated and displayed.
"""

BANKING_TEXT = """
The Customer can transfer money and view account balance.
The Administrator can approve transaction.
An external API is used to process banking requests.
"""


def build_mock_docx_bytes(text: str) -> bytes:
    """Tạo file .docx tối giản trong bộ nhớ để test upload thật."""
    buffer = BytesIO()
    escaped_text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    paragraphs = "".join(
        f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>"
        for line in escaped_text.splitlines()
        if line.strip()
    )
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{paragraphs}</w:body>"
        "</w:document>"
    )

    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<?xml version='1.0' encoding='UTF-8'?><Types xmlns='http://schemas.openxmlformats.org/package/2006/content-types'><Default Extension='xml' ContentType='application/xml'/><Default Extension='rels' ContentType='application/vnd.openxmlformats-package.relationships+xml'/><Override PartName='/word/document.xml' ContentType='application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml'/></Types>")
        archive.writestr("_rels/.rels", "<?xml version='1.0' encoding='UTF-8'?><Relationships xmlns='http://schemas.openxmlformats.org/package/2006/relationships'><Relationship Id='rId1' Type='http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument' Target='word/document.xml'/></Relationships>")
        archive.writestr("word/document.xml", document_xml)

    return buffer.getvalue()


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
    """API extract phải đọc được file .docx thật theo Use Case Document template."""
    docx_bytes = build_mock_docx_bytes(USE_CASE_TEMPLATE_TEXT)

    response = client.post(
        "/extract",
        data={"text": "", "llm_mode": "placeholder"},
        files={
            "uploaded_file": (
                "requirements.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    actor_names = [actor["name"] for actor in payload["actors"]]
    use_case_names = [use_case["name"] for use_case in payload["use_cases"]]
    assert "Guest" in actor_names
    assert "Payment Gateway" in actor_names
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


def test_analyze_and_calculate_returns_expected_hotel_template_metrics() -> None:
    """Hotel Use Case Document đầy đủ phải ra đúng metrics theo rule transaction-count chuẩn."""
    response = client.post(
        "/analyze-and-calculate",
        data={
            "text": FULL_HOTEL_USE_CASE_TEMPLATE_TEXT,
            "llm_mode": "placeholder",
            "technical_complexity_factor": "1.0",
            "environmental_complexity_factor": "1.0",
            "productivity_factor": "20",
            "team_size": "3",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["ucp"]["uaw"] == 10.0
    assert payload["ucp"]["uucw"] == 60.0
    assert payload["ucp"]["uucp"] == 70.0
    assert payload["ucp"]["ucp"] == 70.0
    assert payload["effort"]["hours"] == 1400.0
    assert payload["schedule"]["months"] == 2.92


def test_analyze_and_calculate_returns_expected_banking_metrics() -> None:
    """Banking domain phải ra đúng metrics sau khi thêm rule Transfer Money = complex."""
    response = client.post(
        "/analyze-and-calculate",
        data={
            "text": BANKING_TEXT,
            "llm_mode": "placeholder",
            "technical_complexity_factor": "1.0",
            "environmental_complexity_factor": "1.0",
            "productivity_factor": "20",
            "team_size": "3",
        },
    )

    assert response.status_code == 200

    payload = response.json()
    extracted_use_cases = {
        use_case["name"]: use_case["complexity"]
        for use_case in payload["extraction"]["use_cases"]
    }

    assert extracted_use_cases["Transfer Money"] == "complex"
    assert extracted_use_cases["View Account Balance"] == "simple"
    assert extracted_use_cases["Approve Transaction"] == "average"
    assert payload["ucp"]["uaw"] == 7.0
    assert payload["ucp"]["uucw"] == 30.0
    assert payload["ucp"]["uucp"] == 37.0
    assert payload["ucp"]["ucp"] == 37.0
    assert payload["effort"]["hours"] == 740.0
    assert payload["schedule"]["months"] == 1.54
