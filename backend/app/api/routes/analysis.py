"""Khai báo API cho extraction, UCP calculation và lưu kết quả vào MySQL."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.models.request_models import Actor, UCPRequest, UseCase
from app.models.requests import AnalyzeAndCalculateRequest, ExtractRequest, UcpCalculateRequest
from app.models.responses import AnalysisAndCalculationResponse, ExtractionResponse, UcpCalculationResponse
# Repository dùng để lưu/xem/xóa lịch sử phân tích trong MySQL.
from app.repositories.analysis_repository import AnalysisRepository
from app.services.effort_estimation_service import estimate_effort
from app.services.llm_extractor import LlmExtractionError, extract_requirements
from app.services.schedule_estimation_service import estimate_schedule
from app.services.ucp_calculator import (
    UCPError,
    calculate_actor_weight,
    calculate_ucp_metrics,
    calculate_use_case_weight,
)
from app.utils.file_reader import read_uploaded_text
from app.utils.normalization import normalize_actors, normalize_extraction_result, normalize_structured_use_cases
from app.utils.parser import combine_text_sources
from app.utils.use_case_document_parser import looks_like_use_case_document, parse_use_case_documents
from app.utils.normalization import normalize_use_case_documents

router = APIRouter()


def _build_ucp_core_request(request_model: UcpCalculateRequest) -> tuple[UCPRequest, int, int]:
    """Chuyển dữ liệu từ API model sang model core của UCP calculator."""
    # Nếu description có "Transaction count:", payload này đến từ SRS/use case document có cấu trúc.
    # Khi đó hệ thống giữ tên use case chính thức trong tài liệu và không normalize kiểu free-text quá mạnh.
    structured_payload = _looks_like_structured_use_case_payload(request_model.use_cases)

    # Actor luôn được normalize lại trước khi tính để bỏ trùng và gán complexity đúng chuẩn UCP.
    normalized_actors = normalize_actors(
        request_model.actors,
        source_text="",
        allow_internal_systems=structured_payload,
        preserve_original_labels=structured_payload,
    )

    if structured_payload:
        # Use case có transaction count thì chỉ normalize nhẹ để giữ tên gốc từ tài liệu.
        normalized_use_cases = normalize_structured_use_cases(request_model.use_cases)
    else:
        # Use case từ free-text cần đi qua normalization đầy đủ để bỏ sentence fragment/internal step.
        _, normalized_use_cases = normalize_extraction_result(
            actors=[],
            use_cases=request_model.use_cases,
            source_text="",
        )

    # UCPRequest là model nhỏ, chỉ chứa dữ liệu mà công thức UCP thật sự cần.
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
    """Kiểm tra use case payload có chứa transaction count từ structured document không."""
    return any(
        getattr(use_case, "description", None) and "Transaction count:" in use_case.description
        for use_case in use_cases
    )


def _create_persistence_run(
    repository: AnalysisRepository,
    *,
    title: str,
    input_type: str,
    original_filename: str | None,
    raw_text: str | None,
    source_template_type: str | None,
    llm_mode: str,
    technical_complexity_factor: float,
    environmental_complexity_factor: float,
    productivity_factor: float,
    team_size: int,
    run_type: str,
) -> int | None:
    """Tạo document và analysis_run trước khi xử lý để có nơi lưu log/debug."""
    # Bước 1: tạo document để lưu input gốc trước.
    document_id = repository.create_document(
        # title hiển thị trong mục lịch sử.
        title=title,
        # input_type cho biết text/file/manual payload.
        input_type=input_type,
        # original_filename lưu tên file upload nếu có.
        original_filename=original_filename,
        # raw_text là nội dung gốc; có thể rỗng với /ucp/calculate.
        raw_text=raw_text,
        # source_template_type ghi nhận structured_srs/free_text.
        source_template_type=source_template_type,
        # Khi mới tạo thì đang xử lý nên để running.
        parsing_status="running",
        # Notes giúp giải thích bản ghi được tạo tự động từ API.
        notes="Tạo tự động từ API backend.",
    )
    # Bước 2: tạo analysis_run gắn với document vừa tạo.
    return repository.create_analysis_run(
        # document_id có thể None nếu DB lỗi; repository sẽ bỏ qua an toàn.
        document_id=document_id,
        # llm_mode là mock/placeholder/manual.
        llm_mode=llm_mode,
        # TCF lưu lại đúng input dùng để tính.
        technical_complexity_factor=technical_complexity_factor,
        # ECF lưu lại đúng input dùng để tính.
        environmental_complexity_factor=environmental_complexity_factor,
        # productivity_factor dùng tính effort.
        productivity_factor=productivity_factor,
        # team_size dùng tính schedule.
        team_size=team_size,
        # run_type phân biệt extract_only/calculate_only/analyze_and_calculate.
        run_type=run_type,
    )


def _save_parsed_documents_for_debug(
    repository: AnalysisRepository,
    run_id: int | None,
    raw_text: str,
) -> list[Any]:
    """Parse lại structured document để lưu bản normalized vào bảng parsed_use_case_documents."""
    # Nếu không có run_id, raw_text rỗng hoặc input không giống use case document thì không lưu parsed docs.
    if run_id is None or not raw_text.strip() or not looks_like_use_case_document(raw_text):
        return []

    try:
        # Parse document rồi normalize để dữ liệu lưu DB giống dữ liệu dùng cho extraction.
        parsed_documents = normalize_use_case_documents(parse_use_case_documents(raw_text))
    except Exception as error:  # noqa: BLE001 - parser log không được làm hỏng luồng chính.
        # Nếu parser phụ bị lỗi thì lưu warning, không làm hỏng response chính.
        repository.save_run_log(run_id, "parser", "warning", f"Không lưu được parsed document: {error}")
        return []

    # Lưu từng use case document đã parse vào bảng parsed_use_case_documents.
    for document in parsed_documents:
        repository.save_parsed_use_case_document(run_id, document)

    # Ghi log để biết parser đã lưu bao nhiêu block.
    repository.save_run_log(
        run_id,
        "parser",
        "success",
        f"Đã lưu {len(parsed_documents)} use case document đã parse/normalize.",
    )
    return parsed_documents


def _save_normalized_inputs(
    repository: AnalysisRepository,
    run_id: int | None,
    actors: list[Actor],
    use_cases: list[UseCase],
    raw_text: str | None,
) -> None:
    """Lưu actor/use case sau normalization, tức là đúng dữ liệu dùng để tính UCP."""
    # Nếu DB không tạo được run thì không có nơi để lưu actor/use case.
    if run_id is None:
        return

    # Lưu từng actor đã normalize.
    for actor in actors:
        repository.save_extracted_actor(
            # Gắn actor với analysis_run hiện tại.
            analysis_run_id=run_id,
            # Tên actor đã sạch.
            actor_name=actor.name,
            # actor_type dùng cho báo cáo/debug.
            actor_type=_infer_actor_type(actor.name, actor.complexity),
            # Complexity simple/average/complex.
            complexity=actor.complexity,
            # Weight actor: simple=1, average=2, complex=3.
            weight_value=calculate_actor_weight(actor.complexity),
            # raw_text giúp trace actor lấy từ input nào.
            source_text=raw_text,
        )

    # Lưu từng use case đã normalize.
    for use_case in use_cases:
        repository.save_extracted_use_case(
            # Gắn use case với analysis_run hiện tại.
            analysis_run_id=run_id,
            # Hiện tại payload core chưa giữ use_case_id nên để None.
            use_case_id=None,
            # Tên use case đã sạch.
            use_case_name=use_case.name,
            # Complexity simple/average/complex.
            complexity=use_case.complexity,
            # Weight use case: simple=5, average=10, complex=15.
            weight_value=calculate_use_case_weight(use_case.complexity),
            # Lấy transaction count từ description nếu structured document có.
            transaction_count=_extract_transaction_count(use_case.description),
            # Description giữ thông tin bổ sung như Transaction count.
            description=use_case.description,
            # source_kind giúp phân biệt use case từ structured document hay free text.
            source_kind="structured_document" if _extract_transaction_count(use_case.description) is not None else "free_text",
            # raw_text giúp trace use case lấy từ input nào.
            source_text=raw_text,
        )

    # Ghi log stage normalize sau khi lưu xong actors/use cases.
    repository.save_run_log(
        run_id,
        "normalize",
        "success",
        f"Đã lưu {len(actors)} actor và {len(use_cases)} use case sau normalization.",
    )


def _save_extraction_only_result(
    repository: AnalysisRepository,
    run_id: int | None,
    extraction: ExtractionResponse,
    raw_text: str | None,
) -> None:
    """Lưu kết quả của endpoint /extract khi chưa có bước tính UCP."""
    # Endpoint /extract chỉ có extraction, chưa có calculation.
    if run_id is None:
        return

    # Endpoint /extract chưa tạo UCPRequest, nên lưu trực tiếp response extraction đã được service normalize.
    # Convert ActorItem của API response sang Actor model của calculator để dùng chung helper lưu.
    actors = [Actor(name=actor.name, complexity=actor.complexity) for actor in extraction.actors]
    # Convert UseCaseItem sang UseCase model để dùng chung helper lưu.
    use_cases = [
        UseCase(name=use_case.name, complexity=use_case.complexity, description=use_case.description)
        for use_case in extraction.use_cases
    ]
    _save_normalized_inputs(repository, run_id, actors, use_cases, raw_text)


def _save_calculation_result(
    repository: AnalysisRepository,
    run_id: int | None,
    *,
    core_result: Any,
    effort: Any,
    schedule: Any,
    request_model: UcpCalculateRequest,
) -> None:
    """Lưu metric UAW/UUCW/UCP/Effort/Schedule sau khi tính thành công."""
    # Nếu không có run_id thì không lưu được calculation.
    if run_id is None:
        return

    # Lưu metric cuối cùng vào bảng calculations.
    repository.save_calculation(
        # Gắn calculation với analysis_run hiện tại.
        analysis_run_id=run_id,
        # UAW.
        uaw=core_result.uaw,
        # UUCW.
        uucw=core_result.uucw,
        # UUCP.
        uucp=core_result.uucp,
        # TCF.
        tcf=request_model.technical_complexity_factor,
        # ECF.
        ecf=request_model.environmental_complexity_factor,
        # UCP cuối cùng.
        ucp=core_result.ucp,
        # productivity_factor.
        productivity_factor=request_model.productivity_factor,
        # effort hours.
        effort_hours=effort.hours,
        # person days.
        person_days=effort.person_days,
        # team size.
        team_size=request_model.team_size,
        # schedule months.
        schedule_months=schedule.months,
        # sprint count.
        sprint_count=schedule.sprint_count,
        # recommended team size.
        recommended_team_size=schedule.recommended_team_size,
    )
    # Ghi log stage calculate để biết calculation đã lưu thành công.
    repository.save_run_log(run_id, "calculate", "success", "Đã lưu kết quả UCP/Effort/Schedule.")


def _infer_input_type(text: str, file_name: str | None) -> str:
    """Xác định input đến từ text, file upload hay cả hai."""
    has_text = bool(text and text.strip())
    has_file = bool(file_name)
    if has_text and has_file:
        return "text_and_file"
    if has_file:
        return "file_upload"
    return "plain_text"


def _infer_title(text: str, file_name: str | None, fallback: str) -> str:
    """Tạo title ngắn cho document để nhìn trong database dễ hiểu."""
    if file_name:
        return file_name

    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_line[:120] if first_line else fallback


def _infer_source_template_type(raw_text: str | None) -> str | None:
    """Ghi nhận input là structured SRS hay free-text."""
    if not raw_text or not raw_text.strip():
        return None
    return "structured_srs" if looks_like_use_case_document(raw_text) else "free_text"


def _infer_actor_type(actor_name: str, complexity: str) -> str:
    """Suy ra actor_type đơn giản để lưu database phục vụ báo cáo/demo."""
    lowered_name = actor_name.lower()
    if any(keyword in lowered_name for keyword in ("service", "api", "gateway", "provider", "system")):
        return "external_system"
    if complexity == "complex":
        return "human"
    if complexity == "average":
        return "interface"
    return "external_system"


def _extract_transaction_count(description: str | None) -> int | None:
    """Lấy transaction count từ description của structured use case nếu có."""
    if not description:
        return None

    match = re.search(r"Transaction count:\s*(\d+)", description, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


@router.post("/extract", response_model=ExtractionResponse)
async def extract(
    text: str = Form(default=""),
    llm_mode: str = Form(default="mock"),
    uploaded_file: UploadFile | None = File(default=None),
) -> ExtractionResponse:
    """Nhận text/file, extract actor/use case, sau đó tự động lưu kết quả vào MySQL nếu DB sẵn sàng."""
    file_name, file_text = await read_uploaded_text(uploaded_file)
    raw_text = combine_text_sources(text or None, file_text)
    repository = AnalysisRepository()
    run_id: int | None = None

    try:
        request_model = ExtractRequest(
            source_text=text or None,
            file_name=file_name,
            file_text=file_text,
            llm_mode=llm_mode,
        )
        run_id = _create_persistence_run(
            repository,
            title=_infer_title(raw_text, file_name, "Extraction request"),
            input_type=_infer_input_type(text, file_name),
            original_filename=file_name,
            raw_text=raw_text,
            source_template_type=_infer_source_template_type(raw_text),
            llm_mode=llm_mode,
            technical_complexity_factor=1.0,
            environmental_complexity_factor=1.0,
            productivity_factor=20.0,
            team_size=3,
            run_type="extract_only",
        )
        repository.save_run_log(run_id, "file_read", "success", "Đã đọc/gộp input text và file upload.")
        _save_parsed_documents_for_debug(repository, run_id, raw_text)

        extraction = extract_requirements(request_model)
        repository.save_run_log(run_id, "extract", "success", "Đã extract actor/use case.")
        _save_extraction_only_result(repository, run_id, extraction, raw_text)
        repository.mark_run_success(run_id)
        return extraction
    except ValidationError as error:
        repository.save_run_log(run_id, "validate", "failed", str(error))
        repository.mark_run_failed(run_id, str(error))
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LlmExtractionError as error:
        repository.save_run_log(run_id, "extract", "failed", str(error))
        repository.mark_run_failed(run_id, str(error))
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/ucp/calculate", response_model=UcpCalculationResponse)
def calculate(request_model: UcpCalculateRequest) -> UcpCalculationResponse:
    """Tính UCP từ actor/use case đã có và lưu calculation run vào MySQL."""
    repository = AnalysisRepository()
    run_id = _create_persistence_run(
        repository,
        title="Manual UCP calculation",
        input_type="manual_payload",
        original_filename=None,
        raw_text=None,
        source_template_type=None,
        llm_mode="manual",
        technical_complexity_factor=request_model.technical_complexity_factor,
        environmental_complexity_factor=request_model.environmental_complexity_factor,
        productivity_factor=request_model.productivity_factor,
        team_size=request_model.team_size,
        run_type="calculate_only",
    )

    try:
        core_request, actor_count, use_case_count = _build_ucp_core_request(request_model)
        _save_normalized_inputs(repository, run_id, core_request.actors, core_request.use_cases, raw_text=None)

        core_result = calculate_ucp_metrics(core_request)
        effort = estimate_effort(
            ucp=core_result.ucp,
            productivity_factor=request_model.productivity_factor,
        )
        schedule = estimate_schedule(hours=effort.hours, team_size=request_model.team_size)
        _save_calculation_result(
            repository,
            run_id,
            core_result=core_result,
            effort=effort,
            schedule=schedule,
            request_model=request_model,
        )
        repository.mark_run_success(run_id)
    except ValidationError as error:
        repository.save_run_log(run_id, "validate", "failed", str(error))
        repository.mark_run_failed(run_id, str(error))
        raise HTTPException(status_code=422, detail=str(error)) from error
    except UCPError as error:
        repository.save_run_log(run_id, "calculate", "failed", str(error))
        repository.mark_run_failed(run_id, str(error))
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
    """API gộp: extract actor/use case, tính UCP và tự động lưu toàn bộ kết quả vào MySQL."""
    file_name, file_text = await read_uploaded_text(uploaded_file)
    raw_text = combine_text_sources(text or None, file_text)
    repository = AnalysisRepository()
    run_id: int | None = None

    try:
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
        run_id = _create_persistence_run(
            repository,
            title=_infer_title(raw_text, file_name, "Analysis and calculation request"),
            input_type=_infer_input_type(text, file_name),
            original_filename=file_name,
            raw_text=raw_text,
            source_template_type=_infer_source_template_type(raw_text),
            llm_mode=llm_mode,
            technical_complexity_factor=technical_complexity_factor,
            environmental_complexity_factor=environmental_complexity_factor,
            productivity_factor=productivity_factor,
            team_size=team_size,
            run_type="analyze_and_calculate",
        )
        repository.save_run_log(run_id, "file_read", "success", "Đã đọc/gộp input text và file upload.")
        _save_parsed_documents_for_debug(repository, run_id, raw_text)

        extraction = extract_requirements(request_model)
        repository.save_run_log(run_id, "extract", "success", "Đã extract actor/use case.")
    except ValidationError as error:
        repository.save_run_log(run_id, "validate", "failed", str(error))
        repository.mark_run_failed(run_id, str(error))
        raise HTTPException(status_code=422, detail=str(error)) from error
    except LlmExtractionError as error:
        repository.save_run_log(run_id, "extract", "failed", str(error))
        repository.mark_run_failed(run_id, str(error))
        raise HTTPException(status_code=400, detail=str(error)) from error

    calculation_request = UcpCalculateRequest(
        actors=extraction.actors,
        use_cases=extraction.use_cases,
        technical_complexity_factor=request_model.technical_complexity_factor,
        environmental_complexity_factor=request_model.environmental_complexity_factor,
        productivity_factor=request_model.productivity_factor,
        team_size=request_model.team_size,
    )
    try:
        core_request, actor_count, use_case_count = _build_ucp_core_request(calculation_request)
        _save_normalized_inputs(repository, run_id, core_request.actors, core_request.use_cases, raw_text)

        core_result = calculate_ucp_metrics(core_request)
        effort = estimate_effort(
            ucp=core_result.ucp,
            productivity_factor=request_model.productivity_factor,
        )
        schedule = estimate_schedule(hours=effort.hours, team_size=request_model.team_size)
        _save_calculation_result(
            repository,
            run_id,
            core_result=core_result,
            effort=effort,
            schedule=schedule,
            request_model=calculation_request,
        )
        repository.mark_run_success(run_id)
    except ValidationError as error:
        repository.save_run_log(run_id, "validate", "failed", str(error))
        repository.mark_run_failed(run_id, str(error))
        raise HTTPException(status_code=422, detail=str(error)) from error
    except UCPError as error:
        repository.save_run_log(run_id, "calculate", "failed", str(error))
        repository.mark_run_failed(run_id, str(error))
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


@router.get("/analysis-runs")
def list_analysis_runs() -> dict[str, Any]:
    """Liệt kê các lần phân tích đã lưu trong MySQL."""
    # Endpoint này dùng cho panel "Lịch Sử Tính Toán" trên frontend.
    try:
        # raise_errors=True để nếu DB lỗi thì frontend nhận được lỗi rõ ràng.
        repository = AnalysisRepository(raise_errors=True)
        # Trả về object có key runs để frontend dễ đọc.
        return {"runs": repository.list_saved_runs()}
    except Exception as error:  # noqa: BLE001
        # Nếu MySQL tắt/sai cấu hình thì báo 503 Service Unavailable.
        raise HTTPException(status_code=503, detail=f"Không thể đọc dữ liệu MySQL: {error}") from error


@router.get("/analysis-runs/{run_id}")
def get_analysis_run(run_id: int) -> dict[str, Any]:
    """Lấy chi tiết một lần phân tích đã lưu theo run_id."""
    # Endpoint này dùng khi người dùng bấm "Xem Lại" trong lịch sử.
    try:
        # raise_errors=True để lỗi DB không bị nuốt.
        repository = AnalysisRepository(raise_errors=True)
        # Lấy document, actors, use cases, calculation và logs của run.
        result = repository.get_analysis_result(run_id)
    except Exception as error:  # noqa: BLE001
        # DB lỗi thì trả 503.
        raise HTTPException(status_code=503, detail=f"Không thể đọc dữ liệu MySQL: {error}") from error

    # Không tìm thấy run thì trả 404.
    if result is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy analysis run.")

    # Trả dữ liệu chi tiết cho frontend.
    return result


@router.delete("/analysis-runs/{run_id}")
def delete_analysis_run(run_id: int) -> dict[str, Any]:
    """Xóa một kết quả lịch sử đã lưu trong MySQL."""
    # Endpoint này dùng khi người dùng bấm "Xóa" trong lịch sử.
    try:
        # raise_errors=True để lỗi DB được báo rõ.
        repository = AnalysisRepository(raise_errors=True)
        # Xóa analysis_run; các bảng con tự xóa nhờ ON DELETE CASCADE.
        deleted = repository.delete_analysis_run(run_id)
    except Exception as error:  # noqa: BLE001
        # Nếu MySQL lỗi thì trả 503.
        raise HTTPException(status_code=503, detail=f"Không thể xóa dữ liệu MySQL: {error}") from error

    # Nếu không có dòng nào bị xóa nghĩa là run_id không tồn tại.
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy analysis run để xóa.")

    # Trả kết quả xóa thành công để frontend refresh lịch sử.
    return {"deleted": True, "run_id": run_id}
