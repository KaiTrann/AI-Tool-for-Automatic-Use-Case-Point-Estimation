"""Bộ test cho dịch vụ trích xuất và parser JSON."""

import pytest

from app.models.requests import ExtractRequest
from app.services.llm_extractor import extract_requirements
from app.utils.llm_json_parser import parse_llm_extraction_json

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

COMPLEXITY_RULE_TEXT = """
The Patient can book appointments, update medical notes, and check patient check-in status.
"""

TRANSACTION_FLOW_RULE_TEXT = """
The Guest can book rooms and place order.
The Reader can borrow books.
The Student can enroll in courses.
"""

SEARCH_SIMPLE_RULE_TEXT = """
The Guest can search rooms and view room details.
The Reader can search books and view book details.
The Student can search courses.
"""

BANKING_COMPLEXITY_RULE_TEXT = """
The Customer can transfer money, send money, transfer funds, transfer payment, and view account balance.
The Administrator can approve transaction.
An external API is used to process banking requests.
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


def test_parse_llm_extraction_json_normalizes_values() -> None:
    """Parser phải chuẩn hóa khoảng trắng và complexity."""
    raw_json = """
    {
      "actors": [{"name": "  Admin User  ", "complexity": "COMPLEX"}],
      "use_cases": [{"name": "  Generate Report ", "complexity": "Average"}]
    }
    """

    actors, use_cases = parse_llm_extraction_json(raw_json)

    assert actors[0].name == "Admin User"
    assert actors[0].complexity == "complex"
    assert use_cases[0].name == "Generate Report"
    assert use_cases[0].complexity == "average"


def test_parse_llm_extraction_json_rejects_invalid_complexity() -> None:
    """Parser phải từ chối complexity không hợp lệ."""
    raw_json = """
    {
      "actors": [{"name": "User", "complexity": "expert"}],
      "use_cases": [{"name": "Login", "complexity": "simple"}]
    }
    """

    with pytest.raises(ValueError):
        parse_llm_extraction_json(raw_json)


def test_extract_requirements_supports_mock_mode() -> None:
    """Mock mode phải trả về actor và use case để demo local."""
    request_model = ExtractRequest(
        source_text="The student submits requirements. The admin reviews the report.",
        llm_mode="mock",
    )

    response = extract_requirements(request_model)

    assert len(response.actors) >= 1
    assert len(response.use_cases) >= 1
    assert "pipeline 3 lớp" in response.notes[0].lower()


def test_extract_requirements_supports_placeholder_mode() -> None:
    """Placeholder mode hiện vẫn phải trả về dữ liệu hợp lệ."""
    request_model = ExtractRequest(
        source_text="The user logs in. The system calculates estimation results.",
        llm_mode="placeholder",
    )

    response = extract_requirements(request_model)

    assert len(response.actors) >= 1
    assert len(response.use_cases) >= 1
    assert "placeholder" in response.notes[0].lower()


def test_extract_requirements_supports_use_case_document_template() -> None:
    """Template Use Case Document phải được đọc theo field thay vì chỉ coi là free text."""
    response = extract_requirements(
        ExtractRequest(source_text=USE_CASE_TEMPLATE_TEXT, llm_mode="placeholder")
    )

    actor_complexity = {actor.name: actor.complexity for actor in response.actors}
    use_case_complexity = {
        use_case.name: use_case.complexity for use_case in response.use_cases
    }

    assert actor_complexity == {
        "Guest": "complex",
        "Payment Gateway": "simple",
    }
    assert use_case_complexity["Register"] == "average"
    assert use_case_complexity["Book Room"] == "complex"
    assert any("template" in note.lower() for note in response.notes)


def test_extract_requirements_normalizes_ecommerce_text() -> None:
    """E-commerce phải ra đúng actor chính và use case chức năng ngắn."""
    response = extract_requirements(ExtractRequest(source_text=ECOMMERCE_TEXT, llm_mode="placeholder"))

    actor_names = [actor.name for actor in response.actors]
    use_case_names = [use_case.name for use_case in response.use_cases]

    assert actor_names == ["Customer", "Administrator", "Payment Gateway"]
    assert "System" not in actor_names
    assert "Register" in use_case_names
    assert "Login" in use_case_names
    assert "Browse Products" in use_case_names
    assert "Search Products" in use_case_names
    assert "Add To Cart" in use_case_names
    assert "Place Order" in use_case_names
    assert "Make Payment" in use_case_names
    assert "Manage Products" in use_case_names
    assert any(name.startswith("Confirm") for name in use_case_names)
    assert "Generate Reports" in use_case_names
    assert_no_sentence_fragments(use_case_names)


def test_extract_requirements_preserves_library_domain_nouns() -> None:
    """Library domain không được bị leakage sang Products."""
    response = extract_requirements(ExtractRequest(source_text=LIBRARY_TEXT, llm_mode="mock"))

    actor_names = [actor.name for actor in response.actors]
    use_case_names = [use_case.name for use_case in response.use_cases]

    assert actor_names == ["Reader", "Librarian", "Email Service", "Reporting Service"]
    assert "Search Books" in use_case_names
    assert "Browse Books" in use_case_names
    assert "Borrow Books" in use_case_names
    assert "Manage Book Information" in use_case_names
    assert "Search Products" not in use_case_names
    assert "Overdue Reminders To Readers" not in use_case_names
    assert_no_sentence_fragments(use_case_names)


def test_extract_requirements_excludes_internal_notification_actions() -> None:
    """Các hành vi nền như send reminder hoặc notify user không được tính là use case."""
    notification_text = """
    The Reader can borrow books and return books.
    The System sends overdue reminders to readers.
    The Email Service sends confirmation to the reader.
    """

    response = extract_requirements(ExtractRequest(source_text=notification_text, llm_mode="placeholder"))
    use_case_names = [use_case.name for use_case in response.use_cases]

    assert "Borrow Books" in use_case_names
    assert "Return Books" in use_case_names
    assert "Overdue Reminders To Readers" not in use_case_names
    assert "Send Confirmation" not in use_case_names
    assert "Send Notification" not in use_case_names


def test_extract_requirements_supports_hospital_domain() -> None:
    """Hospital domain mới vẫn phải extract được actor và use case hợp lý."""
    response = extract_requirements(ExtractRequest(source_text=HOSPITAL_TEXT, llm_mode="placeholder"))

    actor_names = [actor.name for actor in response.actors]
    use_case_names = [use_case.name for use_case in response.use_cases]

    assert "Patient" in actor_names
    assert "Doctor" in actor_names
    assert "Receptionist" in actor_names
    assert "Email Service" in actor_names
    assert "Schedule Appointments" in use_case_names
    assert "View Medical Records" in use_case_names
    assert "Review Patient Records" in use_case_names
    assert "Approve Prescriptions" in use_case_names
    assert_no_sentence_fragments(use_case_names)


def test_extract_requirements_supports_hotel_domain() -> None:
    """Hotel booking domain mới vẫn phải extract được actor và use case hợp lý."""
    response = extract_requirements(ExtractRequest(source_text=HOTEL_TEXT, llm_mode="placeholder"))

    actor_names = [actor.name for actor in response.actors]
    use_case_names = [use_case.name for use_case in response.use_cases]

    assert "Guest" in actor_names
    assert "Receptionist" in actor_names
    assert "Payment Gateway" in actor_names
    assert "Email Service" in actor_names
    assert "Search Rooms" in use_case_names
    assert "View Room Details" in use_case_names
    assert "Book Room" in use_case_names
    assert "Make Payment" in use_case_names
    assert "Manage Reservations" in use_case_names
    assert_no_sentence_fragments(use_case_names)


def test_extract_requirements_deduplicates_specific_human_actor_names() -> None:
    """Nếu có Manager và Hotel Manager thì phải giữ actor cụ thể hơn."""
    duplicate_actor_text = """
    The Manager can login.
    The Hotel Manager can manage reservations.
    """

    response = extract_requirements(
        ExtractRequest(source_text=duplicate_actor_text, llm_mode="placeholder")
    )
    actor_names = [actor.name for actor in response.actors]

    assert "Hotel Manager" in actor_names
    assert "Manager" not in actor_names


def test_extract_requirements_refines_hotel_domain_outputs() -> None:
    """Hotel domain phải merge sub-action và chuẩn hóa naming đúng."""
    response = extract_requirements(
        ExtractRequest(source_text=HOTEL_REFINED_TEXT, llm_mode="placeholder")
    )

    actor_complexity = {actor.name: actor.complexity for actor in response.actors}
    use_case_complexity = {
        use_case.name: use_case.complexity for use_case in response.use_cases
    }

    assert actor_complexity == {
        "Guest": "complex",
        "Receptionist": "complex",
        "Hotel Manager": "complex",
        "Payment Gateway": "simple",
        "Email Service": "simple",
    }
    assert "Manage Room Information" in use_case_complexity
    assert "Pay Online" in use_case_complexity
    assert "Update Room Availability" not in use_case_complexity
    assert "Delete Room Information" not in use_case_complexity
    assert use_case_complexity["Book Rooms"] == "complex"
    assert use_case_complexity["Reserve Rooms"] == "complex"
    assert use_case_complexity["Pay Online"] == "average"
    assert use_case_complexity["Check Booking Status"] == "simple"


def test_extract_requirements_refines_education_domain_outputs() -> None:
    """Education domain phải classify Instructor là complex và Create Assignments là average."""
    response = extract_requirements(
        ExtractRequest(source_text=EDUCATION_TEXT, llm_mode="placeholder")
    )

    actor_complexity = {actor.name: actor.complexity for actor in response.actors}
    use_case_complexity = {
        use_case.name: use_case.complexity for use_case in response.use_cases
    }

    assert actor_complexity == {
        "Student": "complex",
        "Instructor": "complex",
        "Education Manager": "complex",
        "Email Service": "simple",
        "Reporting Service": "simple",
    }
    assert use_case_complexity["Create Assignments"] == "average"
    assert use_case_complexity["Book Appointments"] == "complex"
    assert use_case_complexity["Manage Courses"] == "complex"


def test_extract_requirements_keeps_search_and_view_use_cases_simple() -> None:
    """Các use case tra cứu/hiển thị phải luôn được xếp simple theo rule mới."""
    response = extract_requirements(
        ExtractRequest(source_text=SEARCH_SIMPLE_RULE_TEXT, llm_mode="placeholder")
    )

    complexity_by_name = {
        use_case.name: use_case.complexity for use_case in response.use_cases
    }

    assert complexity_by_name["Search Rooms"] == "simple"
    assert complexity_by_name["Search Books"] == "simple"
    assert complexity_by_name["Search Courses"] == "simple"
    assert complexity_by_name["View Room Details"] == "simple"
    assert complexity_by_name["View Book Details"] == "simple"


def test_extract_requirements_full_hotel_template_uses_updated_complexity() -> None:
    """Hotel template đầy đủ phải ra đúng complexity sau khi sửa Search Rooms."""
    response = extract_requirements(
        ExtractRequest(source_text=FULL_HOTEL_USE_CASE_TEMPLATE_TEXT, llm_mode="placeholder")
    )

    actor_complexity = {actor.name: actor.complexity for actor in response.actors}
    use_case_complexity = {
        use_case.name: use_case.complexity for use_case in response.use_cases
    }

    assert actor_complexity == {
        "Guest": "complex",
        "Payment Gateway": "simple",
        "Receptionist": "complex",
        "Hotel Manager": "complex",
    }
    assert use_case_complexity == {
        "Register": "average",
        "Search Rooms": "simple",
        "Book Room": "complex",
        "Cancel Reservation": "average",
        "Manage Room Information": "average",
        "Generate Monthly Report": "average",
    }


def test_extract_requirements_applies_banking_transfer_complex_rules() -> None:
    """Các use case chuyển tiền phải luôn được xếp complex theo rule banking mới."""
    response = extract_requirements(
        ExtractRequest(source_text=BANKING_COMPLEXITY_RULE_TEXT, llm_mode="placeholder")
    )

    complexity_by_name = {
        use_case.name: use_case.complexity for use_case in response.use_cases
    }

    assert complexity_by_name["Transfer Money"] == "complex"
    assert complexity_by_name["Send Money"] == "complex"
    assert complexity_by_name["Transfer Funds"] == "complex"
    assert complexity_by_name["Transfer Payment"] == "complex"
    assert complexity_by_name["View Account Balance"] == "simple"
    assert complexity_by_name["Approve Transaction"] == "average"


def test_extract_requirements_reclassifies_use_case_complexity_by_action() -> None:
    """Complexity phải được reclassify theo action-based rules sau extraction."""
    response = extract_requirements(
        ExtractRequest(source_text=COMPLEXITY_RULE_TEXT, llm_mode="placeholder")
    )

    complexity_by_name = {
        use_case.name.lower(): use_case.complexity for use_case in response.use_cases
    }

    assert complexity_by_name["book appointments"] == "complex"
    assert complexity_by_name["update medical notes"] == "average"
    assert complexity_by_name["check patient check-in status"] == "simple"


def test_extract_requirements_applies_transaction_flow_complex_rules() -> None:
    """Các use case giao dịch nhiều bước phải được xếp complex theo rule mới."""
    response = extract_requirements(
        ExtractRequest(source_text=TRANSACTION_FLOW_RULE_TEXT, llm_mode="placeholder")
    )

    complexity_by_name = {
        use_case.name.lower(): use_case.complexity for use_case in response.use_cases
    }

    assert complexity_by_name["book rooms"] == "complex"
    assert complexity_by_name["borrow books"] == "complex"
    assert complexity_by_name["enroll in courses"] == "complex"
    assert complexity_by_name["place order"] == "complex"


def assert_no_sentence_fragments(use_case_names: list[str]) -> None:
    """Không cho phép sentence fragment lọt vào output."""
    for name in use_case_names:
        lowered_name = name.lower()
        assert not lowered_name.startswith("the ")
        assert not lowered_name.startswith("after ")
        assert "allows" not in lowered_name
