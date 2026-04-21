"""Khai báo các API cho chức năng trích xuất và tính toán UCP từ free-text input."""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.models.request_models import Actor, UCPRequest, UseCase
from app.models.requests import AnalyzeAndCalculateRequest, ExtractRequest, UcpCalculateRequest
from app.models.responses import AnalysisAndCalculationResponse, ExtractionResponse, UcpCalculationResponse
from app.services.effort_estimation_service import estimate_effort
from app.services.llm_extractor import LlmExtractionError, extract_requirements
from app.services.schedule_estimation_service import estimate_schedule
from app.services.ucp_calculator import UCPError, calculate_ucp_metrics
from app.utils.file_reader import read_uploaded_text
from app.utils.normalization import normalize_actors, normalize_extraction_result, normalize_structured_use_cases

router = APIRouter()


def _build_ucp_core_request(request_model: UcpCalculateRequest) -> tuple[UCPRequest, int, int]:
    """Chuyển dữ liệu từ model API sang model dùng cho bộ tính UCP.

    Dữ liệu luôn được normalize lại trước khi tính toán
    để đảm bảo Layer 3 chỉ dùng dữ liệu đã chuẩn hóa.
    """
    # Dù dữ liệu đi từ frontend hay từ endpoint analyze-and-calculate,
    # backend vẫn normalize lại một lần nữa trước khi tính.
    # Điều này giúp tránh trường hợp frontend gửi:
    # - actor bị trùng
    # - use case bị sai tên
    # - complexity chưa đúng rule
    # Actor luôn được normalize lại để đảm bảo:
    # - bỏ trùng
    # - chuẩn hóa tên
    # - complexity đúng theo chuẩn UCP
    # Nếu payload đến từ structured use case document,
    # description thường đã có "Transaction count: ...".
    # Khi đó cần giữ nguyên tên use case chính thức từ tài liệu,
    # không chạy lại normalize kiểu free-text để tránh mất use case hợp lệ.
    structured_payload = _looks_like_structured_use_case_payload(request_model.use_cases)
    normalized_actors = normalize_actors(
        request_model.actors,
        source_text="",
        allow_internal_systems=structured_payload,
        preserve_original_labels=structured_payload,
    )

    if structured_payload:
        # Payload đến từ SRS / Use Case Document đã có transaction count,
        # nên phải giữ tên use case chính thức từ tài liệu.
        normalized_use_cases = normalize_structured_use_cases(request_model.use_cases)
    else:
        # Payload đến từ free-text thì đi qua normalization chung.
        _, normalized_use_cases = normalize_extraction_result(
            actors=[],
            use_cases=request_model.use_cases,
            source_text="",
        )

    # Chuyển về model UCPRequest của lớp tính toán core.
    # Lớp này chỉ quan tâm đến danh sách actor/use case đã sạch.
    core_request = UCPRequest(
        actors=[
            Actor(name=actor.name, complexity=actor.complexity)
            for actor in normalized_actors
        ],
        use_cases=[
            UseCase(
                name=use_case.name,
                complexity=use_case.complexity,
                description=use_case.description,
            )
            for use_case in normalized_use_cases
        ],
        tcf=request_model.technical_complexity_factor,
        ecf=request_model.environmental_complexity_factor,
        productivity_factor=request_model.productivity_factor,
    )
    return core_request, len(normalized_actors), len(normalized_use_cases)


def _looks_like_structured_use_case_payload(use_cases: list) -> bool:
    """Kiểm tra payload use case có đến từ structured document hay không."""
    return any(
        getattr(use_case, "description", None) and "Transaction count:" in use_case.description
        for use_case in use_cases
    )


@router.post("/extract", response_model=ExtractionResponse)
async def extract(
    text: str = Form(default=""),
    llm_mode: str = Form(default="mock"),
    uploaded_file: UploadFile | None = File(default=None),
) -> ExtractionResponse:
    """Nhận Requirements Text hoặc nội dung text từ file upload rồi trả về actor/use case."""
    # File upload trong prototype này được đọc như một nguồn text bổ sung.
    # Nếu không có file, hàm sẽ trả về None cho file_name và file_text.
    # Đọc file upload nếu người dùng gửi kèm.
    file_name, file_text = await read_uploaded_text(uploaded_file)
    try:
        # Gộp dữ liệu form thành model để Pydantic tự validate đầu vào.
        request_model = ExtractRequest(
            source_text=text or None,
            file_name=file_name,
            file_text=file_text,
            llm_mode=llm_mode,
        )
        # Toàn bộ logic extraction nằm trong service để route luôn mỏng và dễ đọc.
        # Service extraction sẽ tự quyết định:
        # - parse SRS/use case document
        # hoặc
        # - extract từ free-text
        return extract_requirements(request_model)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LlmExtractionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/ucp/calculate", response_model=UcpCalculationResponse)
def calculate(request_model: UcpCalculateRequest) -> UcpCalculationResponse:
    """Tính UAW, UUCW, UCP, effort và schedule từ dữ liệu actor/use case đã được normalize."""
    try:
        # Bước 1: normalize lại dữ liệu và chuyển sang model core.
        # Chuẩn hóa dữ liệu đầu vào trước rồi mới chuyển vào bộ tính UCP lõi.
        core_request, actor_count, use_case_count = _build_ucp_core_request(request_model)

        # Bước 2: tính các giá trị UCP cốt lõi.
        # Tính UAW, UUCW, UUCP, UCP.
        core_result = calculate_ucp_metrics(core_request)

        # Bước 3: từ UCP suy ra Effort và Schedule.
        # Tính effort và schedule từ UCP sau khi đã có kết quả lõi.
        effort = estimate_effort(
            ucp=core_result.ucp,
            productivity_factor=request_model.productivity_factor,
        )
        schedule = estimate_schedule(hours=effort.hours, team_size=request_model.team_size)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except UCPError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return UcpCalculationResponse(
        ucp={
            "uaw": core_result.uaw,
            "uucw": core_result.uucw,
            "uucp": core_result.uucp,
            "ucp": core_result.ucp,
            "actor_count": actor_count,
            "use_case_count": use_case_count,
            "technical_complexity_factor": request_model.technical_complexity_factor,
            "environmental_complexity_factor": request_model.environmental_complexity_factor,
        },
        effort=effort,
        schedule=schedule,
    )


@router.post("/analyze-and-calculate", response_model=AnalysisAndCalculationResponse)
async def analyze_and_calculate(
    text: str = Form(default=""),
    llm_mode: str = Form(default="mock"),
    technical_complexity_factor: float = Form(default=1.0),
    environmental_complexity_factor: float = Form(default=1.0),
    productivity_factor: float = Form(default=20.0),
    team_size: int = Form(default=3),
    uploaded_file: UploadFile | None = File(default=None),
) -> AnalysisAndCalculationResponse:
    """API gộp: vừa trích xuất từ free-text input vừa tính toán kết quả UCP."""
    # Endpoint tổng hợp:
    # nhận text/file, trích xuất, rồi tính UCP trong cùng một request.
    file_name, file_text = await read_uploaded_text(uploaded_file)
    try:
        # Tạo model đầu vào cho luồng "extract rồi calculate".
        request_model = AnalyzeAndCalculateRequest(
            source_text=text or None,
            file_name=file_name,
            file_text=file_text,
            llm_mode=llm_mode,
            technical_complexity_factor=technical_complexity_factor,
            environmental_complexity_factor=environmental_complexity_factor,
            productivity_factor=productivity_factor,
            team_size=team_size,
        )

        # Giai đoạn 1: trích xuất dữ liệu thô + normalize actor/use case.
        extraction = extract_requirements(request_model)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LlmExtractionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    # Giai đoạn 2: chuyển kết quả extraction thành payload cho bộ tính UCP.
    # Dùng chính kết quả extraction đã chuẩn hóa để tạo payload tính UCP.
    calculation_request = UcpCalculateRequest(
        actors=extraction.actors,
        use_cases=extraction.use_cases,
        technical_complexity_factor=request_model.technical_complexity_factor,
        environmental_complexity_factor=request_model.environmental_complexity_factor,
        productivity_factor=request_model.productivity_factor,
        team_size=request_model.team_size,
    )
    try:
        # Giai đoạn 3: tính toán toàn bộ chỉ số cuối cùng.
        # Chuẩn hóa lần cuối trước khi tính để chắc chắn pipeline luôn dùng dữ liệu sạch.
        core_request, actor_count, use_case_count = _build_ucp_core_request(calculation_request)
        core_result = calculate_ucp_metrics(core_request)
        effort = estimate_effort(
            ucp=core_result.ucp,
            productivity_factor=request_model.productivity_factor,
        )
        schedule = estimate_schedule(hours=effort.hours, team_size=request_model.team_size)
    except ValidationError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except UCPError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return AnalysisAndCalculationResponse(
        extraction=extraction,
        ucp={
            "uaw": core_result.uaw,
            "uucw": core_result.uucw,
            "uucp": core_result.uucp,
            "ucp": core_result.ucp,
            "actor_count": actor_count,
            "use_case_count": use_case_count,
            "technical_complexity_factor": request_model.technical_complexity_factor,
            "environmental_complexity_factor": request_model.environmental_complexity_factor,
        },
        effort=effort,
        schedule=schedule,
    )
