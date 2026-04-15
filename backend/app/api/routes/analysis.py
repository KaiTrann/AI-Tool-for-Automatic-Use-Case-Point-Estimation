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
from app.utils.normalization import normalize_extraction_result

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
    normalized_actors, normalized_use_cases = normalize_extraction_result(
        actors=request_model.actors,
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


@router.post("/extract", response_model=ExtractionResponse)
async def extract(
    text: str = Form(default=""),
    llm_mode: str = Form(default="mock"),
    uploaded_file: UploadFile | None = File(default=None),
) -> ExtractionResponse:
    """Nhận Requirements Text hoặc nội dung text từ file upload rồi trả về actor/use case."""
    # File upload trong prototype này được đọc như một nguồn text bổ sung.
    # Nếu không có file, hàm sẽ trả về None cho file_name và file_text.
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
        core_request, actor_count, use_case_count = _build_ucp_core_request(request_model)

        # Bước 2: tính các giá trị UCP cốt lõi.
        core_result = calculate_ucp_metrics(core_request)

        # Bước 3: từ UCP suy ra Effort và Schedule.
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
