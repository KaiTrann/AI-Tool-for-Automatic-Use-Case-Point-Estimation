"""Regression test cho template IEEE/SRS mới của dự án UCP."""

from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.main import app
from app.models.requests import ExtractRequest
from app.services.llm_extractor import extract_requirements
from app.utils.use_case_document_parser import parse_use_case_documents

client = TestClient(app)

IEEE_HR_SRS_TEXT = """
1. Introduction
This document describes the HR-Payroll management system.

5.2 List of Use Case
Use Case ID | Use Case Name | Functional Requirement
UC.01 | Manage Employee Records / Hoạch định nhu cầu nhân sự | FR-01
UC.02 | Manage Employee Lifecycle / Vòng đời nhân viên | FR-02
UC.03 | Manage Organizational Structure / Quản lý cơ cấu tổ chức | FR-03
UC.04 | Onboarding / Offboarding Employee | FR-04
UC.05 | Record Working Time / Ghi nhận thời gian làm việc | FR-05
UC.06 | Manage Work Shifts / Quản lý ca làm việc | FR-06
UC.07 | Control Overtime & Leave / Kiểm soát tăng ca | FR-07
UC.08 | Generate Attendance Summary / Tổng hợp dữ liệu công | FR-08
UC.13 | Manage KPI / OKR | FR-13
UC.14 | Evaluate Employee Performance | FR-14
UC.15 | Generate HR Reports / Phân tích dữ liệu HR | FR-15
UC.18 | View Dashboard Analytics / Dashboard quản trị | FR-18

5.4 Use Case Specification

Use Case ID: UC.01
Use Case Name: Manage Employee Records / Hoạch định nhu cầu nhân sự
Created by: Analyst Team
Last updated by: BA Team
Date Created: 2026-04-18
Date last updated: 2026-04-19
Actors: HR Manager, Admin, System
Brief Description: Quản lý hồ sơ nhân viên và cập nhật dữ liệu nhân sự.
Goal: Manage employee profile data.
Trigger: HR Manager opens the employee module.
Pre-conditions: Admin has configured access rights.
Post-conditions: Employee records are updated.
Main Flow
1. HR Manager opens employee records.
2. System displays employee list.
3. HR Manager creates or updates employee information.
4. System validates the entered information.
5. System saves employee records.
Priority: High
Business Rule: Employee ID must be unique.

Use Case ID: UC.05
Use Case Name: Record Working Time / Ghi nhận thời gian làm việc
Actors: Employee, System
Brief Description: Nhân viên ghi nhận giờ làm việc hàng ngày.
Trigger: Employee opens attendance form.
Pre-conditions: Employee account is active.
Post-conditions: Working time is stored.
Main Flow
1. Employee opens the attendance page.
2. Employee enters working time.
3. System validates the time sheet.
4. System stores attendance data.

Use Case ID: UC.08
Use Case Name: Generate Attendance Summary / Tổng hợp dữ liệu công
Actors: Payroll Manager, Dashboard System
Brief Description: Tổng hợp dữ liệu công để phục vụ payroll.
Goal: Generate summary for payroll.
Trigger: Payroll Manager requests attendance summary.
Pre-conditions: Attendance data exists.
Post-conditions: Attendance summary is displayed.
Main Flow
1. Payroll Manager opens attendance summary.
2. System collects attendance data.
3. System aggregates working hours.
4. Dashboard System generates summary dashboard.
5. System displays the summary.
Alternative Flow
1. If data is incomplete, System shows a warning.

Use Case ID: UC.14
Use Case Name: Evaluate Employee Performance
Actors: Department Manager, Line Manager
Brief Description: Đánh giá hiệu suất nhân viên theo KPI / OKR.
Trigger: Department Manager opens performance evaluation.
Pre-conditions: KPI data exists.
Post-conditions: Evaluation result is stored.
Main Flow
1. Department Manager opens evaluation screen.
2. Line Manager enters KPI results.
3. System calculates performance score.
4. Department Manager confirms the evaluation.
5. System stores the result.
"""

IEEE_HR_REAL_STYLE_SNIPPET = """
5.4 Use Case Specification:
Hoạch định nhu cầu nhân sự
Use Case ID
UC.01
Use Case Name
Hoạch định nhu cầu nhân sự
Created by
Huy Pham Phan Hoang
Last updated by
Huy Pham Phan Hoang
Date Created
Feb 02, 2026
Date last updated
Feb 02, 2026
Actors
HR Manager, System
Brief Description
Hệ thống cho phép quản lý hồ sơ nhân viên.
Goal
Đảm bảo hồ sơ nhân viên được lưu trữ đầy đủ.
Trigger
HR Manager truy cập module quản lý hồ sơ nhân viên.
Pre-conditions
Người dùng đăng nhập với quyền HR Manager.
Post-conditions
Dữ liệu nhân viên được cập nhật thành công.
Main Flow
Step
Actor Action
System Response
1
Mở module quản lý hồ sơ nhân viên
Hiển thị danh sách nhân viên hiện tại
2
Chọn thêm mới hoặc chỉnh sửa
Hiển thị form nhập liệu
3
Nhập thông tin và nhấn lưu
Kiểm tra tính hợp lệ của dữ liệu
4
Lưu bản ghi vào CSDL
5
Xem lại dữ liệu đã lưu
Hiển thị thông báo thành công
Priority
High
Business Rule
BR-01, BR-05
"""

IEEE_HR_REAL_STYLE_LIST_SNIPPET = """
5.2 List of Use Case
<Liệt kê các use case>
Use case ID
Use case name
Functional Req.
UC.19
User Login
FR19
UC.20
Manage Users
FR19
UC.21
Manage Role-Based Access Control (RBAC)
FR20
UC.22
View Audit Logs
FR20
5.3 Use Case Diagram Overview
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


def test_ieee_srs_parser_reads_list_and_specification_blocks() -> None:
    """Parser phải đọc được cả list index lẫn block specification chi tiết."""
    documents = parse_use_case_documents(IEEE_HR_SRS_TEXT)
    document_map = {document.use_case_id: document for document in documents}

    assert len(documents) == 12

    assert document_map["UC.01"].use_case_name == "Manage Employee Records / Hoạch định nhu cầu nhân sự"
    assert document_map["UC.02"].use_case_name == "Manage Employee Lifecycle / Vòng đời nhân viên"
    assert document_map["UC.18"].use_case_name == "View Dashboard Analytics / Dashboard quản trị"

    assert document_map["UC.01"].functional_requirement == "FR-01"
    assert document_map["UC.05"].actors == ["Employee", "System"]
    assert document_map["UC.14"].actors == ["Department Manager", "Line Manager"]
    assert len(document_map["UC.08"].main_flow_steps) == 5


def test_ieee_srs_parser_handles_real_style_metadata_lines() -> None:
    """Parser phải bỏ metadata tách dòng kiểu file IEEE thật, không để dính vào tên use case."""
    documents = parse_use_case_documents(IEEE_HR_REAL_STYLE_SNIPPET)

    assert len(documents) == 1
    assert documents[0].use_case_id == "UC.01"
    assert documents[0].use_case_name == "Hoạch định nhu cầu nhân sự"
    assert documents[0].actors == ["HR Manager", "System"]
    assert len(documents[0].main_flow_steps) == 5


def test_ieee_srs_parser_reads_real_style_stacked_list_section() -> None:
    """Parser phải đọc được bảng list bị bung thành từng dòng như file IEEE thật."""
    documents = parse_use_case_documents(IEEE_HR_REAL_STYLE_LIST_SNIPPET)
    document_map = {document.use_case_id: document for document in documents}

    assert len(documents) == 4
    assert document_map["UC.19"].use_case_name == "User Login"
    assert document_map["UC.20"].functional_requirement == "FR19"
    assert document_map["UC.21"].use_case_name == "Manage Role-Based Access Control (RBAC)"
    assert document_map["UC.22"].use_case_name == "View Audit Logs"


def test_ieee_srs_extraction_keeps_expected_actor_and_use_case_index() -> None:
    """Extraction phải giữ đủ actor và use case chính từ template IEEE/SRS mới."""
    response = extract_requirements(
        ExtractRequest(source_text=IEEE_HR_SRS_TEXT, llm_mode="placeholder")
    )

    actor_complexity = {actor.name: actor.complexity for actor in response.actors}
    use_case_names = [use_case.name for use_case in response.use_cases]

    assert actor_complexity == {
        "HR Manager": "complex",
        "Admin": "complex",
        "System": "simple",
        "Employee": "complex",
        "Payroll Manager": "complex",
        "Dashboard System": "simple",
        "Department Manager": "complex",
        "Line Manager": "complex",
    }

    assert "Manage Employee Records / Hoạch Định Nhu Cầu Nhân Sự" in use_case_names
    assert "Manage Employee Lifecycle / Vòng Đời Nhân Viên" in use_case_names
    assert "Manage Organizational Structure / Quản Lý Cơ Cấu Tổ Chức" in use_case_names
    assert "Onboarding / Offboarding Employee" in use_case_names
    assert "Record Working Time / Ghi Nhận Thời Gian Làm Việc" in use_case_names
    assert "Manage Work Shifts / Quản Lý Ca Làm Việc" in use_case_names
    assert "Control Overtime & Leave / Kiểm Soát Tăng Ca" in use_case_names
    assert "Generate Attendance Summary / Tổng Hợp Dữ Liệu Công" in use_case_names
    assert "Manage KPI / OKR" in use_case_names
    assert "Evaluate Employee Performance" in use_case_names
    assert "Generate HR Reports / Phân Tích Dữ Liệu HR" in use_case_names
    assert "View Dashboard Analytics / Dashboard Quản Trị" in use_case_names


def test_ieee_srs_docx_upload_works_end_to_end() -> None:
    """Upload file .docx IEEE/SRS phải đi được toàn bộ pipeline."""
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
                "ieee_hr_srs.docx",
                build_mock_docx_bytes(IEEE_HR_SRS_TEXT),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200

    payload = response.json()
    actor_names = [actor["name"] for actor in payload["extraction"]["actors"]]
    use_case_names = [use_case["name"] for use_case in payload["extraction"]["use_cases"]]

    assert "HR Manager" in actor_names
    assert "Dashboard System" in actor_names
    assert "Generate Attendance Summary / Tổng Hợp Dữ Liệu Công" in use_case_names
    assert payload["ucp"]["actor_count"] == 8
    assert payload["ucp"]["use_case_count"] == 12
