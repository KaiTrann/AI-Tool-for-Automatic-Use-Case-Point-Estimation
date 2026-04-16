"""Regression test cho pipeline Use Case Specification chuẩn nội bộ."""

from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import app
from app.models.requests import ExtractRequest
from app.services.use_case_classifier import count_transactions_from_main_flow
from app.services.llm_extractor import extract_requirements
from app.utils.actor_normalizer import normalize_actor_list
from app.utils.use_case_document_parser import parse_use_case_documents

client = TestClient(app)

LIBRARY_SRS_TEXT = """
Library Management Use Case Document
Use Case 1: Search Book
Use Case ID
UC-LIB-01
Use Case Name
Search Book
Primary Actor
Reader
Secondary Actor
Library Database
Description
Reader searches the catalogue and the database returns matching book records.
Trigger
Reader wants to find a book.
Preconditions
The library catalogue is available.
Main Success Scenario
1. Reader enters search keywords.
2. System sends the query to Library Database.
3. System displays the matching books.
Alternative Flows
1. If no book is found, the system shows a no-result message.
Postconditions
Search results are displayed.
Use Case 2: Borrow Book
Use Case ID
UC-LIB-02
Use Case Name
Borrow Book
Primary Actor
Reader
Secondary Actor
Library Database
Description
Reader borrows an available book recorded in the library database.
Trigger
Reader selects a book to borrow.
Preconditions
The book is available.
Main Success Scenario
1. Reader selects the book.
2. System checks the availability in Library Database.
3. System records the loan transaction.
4. System updates the due date.
5. System displays the borrowing result.
Postconditions
The book is borrowed successfully.
"""

HOTEL_USE_CASE_TEXT = """
Use Case 1: Search Rooms
Use Case ID: UC-HT-01
Use Case Name: Search Rooms
Primary Actor: Guest
Secondary Actor: Room Database
Description: Guest searches room availability and room data is returned from the database.
Trigger: Guest wants to find an available room.
Preconditions: The booking system is online.
Main Success Scenario
1. Guest enters search criteria.
2. System checks Room Database.
3. System displays available rooms.
Postconditions: Available rooms are shown.
Use Case 2: Book Room
Use Case ID: UC-HT-02
Use Case Name: Book Room
Primary Actor: Guest
Secondary Actor: Payment Gateway
Description: Guest books a room and completes online payment through an external API.
Trigger: Guest chooses a room to reserve.
Preconditions: A room is available.
Main Success Scenario
1. Guest selects a room.
2. System displays booking information.
3. Guest enters booking details.
4. System validates the booking data.
5. Guest confirms the booking.
6. System redirects payment to Payment Gateway.
7. Payment Gateway returns the payment status.
8. System records the reservation.
Postconditions: The room is booked.
"""

BANKING_USE_CASE_TEXT = """
Use Case 1: View Account Balance
Use Case ID: UC-BK-01
Use Case Name: View Account Balance
Primary Actor: Customer
Secondary Actor: Core Banking Database
Description: Customer views account balance from the banking database.
Trigger: Customer opens the balance page.
Preconditions: Customer is logged in.
Main Success Scenario
1. Customer requests account balance.
2. System reads balance data from Core Banking Database.
3. System displays the account balance.
Postconditions: Account balance is shown.
Use Case 2: Transfer Money
Use Case ID: UC-BK-02
Use Case Name: Transfer Money
Primary Actor: Customer
Secondary Actor: Banking API
Description: Customer transfers money through an external API based banking service.
Trigger: Customer starts a transfer.
Preconditions: Customer has sufficient balance.
Main Success Scenario
1. Customer enters recipient information.
2. Customer enters transfer amount.
3. System validates sender account.
4. System validates recipient account.
5. System checks available balance.
6. Customer confirms the transfer.
7. System sends the transfer request to Banking API.
8. System displays the transfer result.
Postconditions: Transfer is recorded.
"""

PLAIN_REQUIREMENTS_TEXT = """
The system allows a Customer to register and log in.
The Customer can browse products, search for products, add products to the shopping cart, place an order, and make payment.
The Administrator can log in and generate reports.
An external Payment Gateway is used to process payments.
"""

LIBRARY_SRS_NOISY_TEXT = """
Table of Contents
1. Introduction ................................ 1
2.4.5 Use Case Specification ................... 12
List of use cases
UC.01 Login
UC.02 Search books

Revision History
Create by: Analyst Team
Last updated by: Project Manager
Date created: 2026-01-10
Date last updated: 2026-02-11

2.4.5 Use Case Specification

UC.01: Login
Create by: Analyst Team
Last updated by: Project Manager
Date created: 2026-01-10
Use case ID: UC.01
Use case name: Login
Actor: Users of the system, including: Librarian,Stocker,Reading Management Staff
Description: Users sign in to the system.
Trigger: User opens the login page.
Preconditions: User account exists.
Main Success Scenario
1. User enters username and password.
2. System validates the credentials.
3. System opens the dashboard.
Postconditions: User is logged in.

UC.02: Search books
Create by: Analyst Team
Date created: 2026-01-12
Use case ID: UC.02
Use case name: Search books
Actor: Including: Librarian, Stocker
Description: Staff search books in the catalogue.
Trigger: Staff wants to find a book.
Preconditions: Staff is logged in.
Main Success Scenario
1. Staff enters search keywords.
2. System retrieves matching books.
3. System displays search results.
Postconditions: Matching books are displayed.
"""


def build_mock_docx_bytes(text: str) -> bytes:
    """Tạo file .docx nhỏ trong bộ nhớ để test upload."""
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


def test_uploaded_library_srs_uses_standard_document_pipeline() -> None:
    """Library SRS upload phải được parse theo template chuẩn và tính complexity theo số transaction."""
    response = client.post(
        "/analyze-and-calculate",
        data={
            "text": "",
            "llm_mode": "placeholder",
            "technical_complexity_factor": "1.0",
            "environmental_complexity_factor": "1.0",
            "productivity_factor": "20",
            "team_size": "3",
        },
        files={
            "uploaded_file": (
                "library_srs.docx",
                build_mock_docx_bytes(LIBRARY_SRS_TEXT),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200

    payload = response.json()
    actors = {actor["name"]: actor["complexity"] for actor in payload["extraction"]["actors"]}
    use_cases = {use_case["name"]: use_case["complexity"] for use_case in payload["extraction"]["use_cases"]}

    assert actors == {
        "Reader": "complex",
        "Library Database": "average",
    }
    assert use_cases == {
        "Search Book": "simple",
        "Borrow Book": "average",
    }
    assert payload["ucp"]["uaw"] == 5.0
    assert payload["ucp"]["uucw"] == 15.0
    assert payload["ucp"]["uucp"] == 20.0
    assert any("schema chuẩn nội bộ" in note.lower() for note in payload["extraction"]["notes"])


def test_hotel_use_case_document_uses_transaction_count_for_complexity() -> None:
    """Hotel use case document phải ưu tiên số transaction thay vì keyword cứng."""
    response = extract_requirements(
        ExtractRequest(source_text=HOTEL_USE_CASE_TEXT, llm_mode="placeholder")
    )

    actors = {actor.name: actor.complexity for actor in response.actors}
    use_cases = {use_case.name: use_case.complexity for use_case in response.use_cases}

    assert actors == {
        "Guest": "complex",
        "Room Database": "average",
        "Payment Gateway": "simple",
    }
    assert use_cases == {
        "Search Rooms": "simple",
        "Book Room": "complex",
    }


def test_banking_use_case_document_uses_transaction_count_for_complexity() -> None:
    """Banking document phải xếp Transfer Money là complex vì có hơn 7 transaction."""
    response = extract_requirements(
        ExtractRequest(source_text=BANKING_USE_CASE_TEXT, llm_mode="placeholder")
    )

    actors = {actor.name: actor.complexity for actor in response.actors}
    use_cases = {use_case.name: use_case.complexity for use_case in response.use_cases}

    assert actors == {
        "Customer": "complex",
        "Core Banking Database": "average",
        "Banking API": "simple",
    }
    assert use_cases == {
        "View Account Balance": "simple",
        "Transfer Money": "complex",
    }


def test_plain_requirements_text_still_uses_fallback_mode() -> None:
    """Nếu input không phải Use Case Specification thì hệ thống phải fallback về requirements-text mode."""
    response = extract_requirements(
        ExtractRequest(source_text=PLAIN_REQUIREMENTS_TEXT, llm_mode="placeholder")
    )

    actor_names = [actor.name for actor in response.actors]
    use_case_names = [use_case.name for use_case in response.use_cases]

    assert "Customer" in actor_names
    assert "Payment Gateway" in actor_names
    assert "System" not in actor_names
    assert "Register" in use_case_names
    assert "Login" in use_case_names
    assert "Place Order" in use_case_names
    assert all("schema chuẩn nội bộ" not in note.lower() for note in response.notes)


def test_actor_normalizer_removes_including_prefixes() -> None:
    """Actor normalizer phải bỏ prefix kiểu 'Including:' và tách danh sách actor sạch."""
    actors = normalize_actor_list(
        "Users of the system, including: Librarian,Stocker,Reading Management Staff"
    )

    assert actors == [
        "Librarian",
        "Stocker",
        "Reading Management Staff",
    ]


def test_library_srs_parser_ignores_toc_and_metadata() -> None:
    """Parser phải chỉ lấy UC block thật, bỏ TOC, metadata và list-of-use-cases."""
    documents = parse_use_case_documents(LIBRARY_SRS_NOISY_TEXT)

    assert len(documents) == 2

    login_document = documents[0]
    search_document = documents[1]

    assert login_document.use_case_name == "Login"
    assert login_document.primary_actor == "Librarian"
    assert login_document.secondary_actors == ["Stocker", "Reading Management Staff"]
    assert count_transactions_from_main_flow(login_document) == 3

    assert search_document.use_case_name == "Search books"
    assert search_document.primary_actor == "Librarian"
    assert search_document.secondary_actors == ["Stocker"]
    assert count_transactions_from_main_flow(search_document) == 3


def test_library_srs_extraction_classifies_human_roles_as_complex() -> None:
    """Librarian, Stocker, Reading Management Staff phải đều được classify là complex."""
    response = extract_requirements(
        ExtractRequest(source_text=LIBRARY_SRS_NOISY_TEXT, llm_mode="placeholder")
    )

    actors = {actor.name: actor.complexity for actor in response.actors}
    use_cases = {use_case.name: use_case.complexity for use_case in response.use_cases}

    assert actors == {
        "Librarian": "complex",
        "Stocker": "complex",
        "Reading Management Staff": "complex",
    }
    assert use_cases["Login"] == "simple"
    assert use_cases["Search Books"] == "simple"
