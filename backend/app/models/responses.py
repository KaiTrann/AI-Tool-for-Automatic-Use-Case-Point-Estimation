"""Các model response chính của backend."""

from pydantic import BaseModel, Field

from app.models.requests import ActorItem, UseCaseItem


class HealthResponse(BaseModel):
    """Response cho API kiểm tra trạng thái backend."""

    status: str
    service: str


class ExtractionResponse(BaseModel):
    """Kết quả trích xuất actor và use case."""

    actors: list[ActorItem] = Field(default_factory=list)
    use_cases: list[UseCaseItem] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class UcpBreakdownResponse(BaseModel):
    """Chi tiết từng giá trị trung gian trong công thức UCP."""

    uaw: float
    uucw: float
    uucp: float
    ucp: float
    actor_count: int
    use_case_count: int
    technical_complexity_factor: float
    environmental_complexity_factor: float


class EffortEstimateResponse(BaseModel):
    """Kết quả ước lượng effort."""

    hours: float
    person_days: float
    productivity_factor: float


class ScheduleEstimateResponse(BaseModel):
    """Kết quả ước lượng lịch trình."""

    months: float
    recommended_team_size: int
    sprint_count: int


class UcpCalculationResponse(BaseModel):
    """Response cho API chỉ tính UCP."""

    ucp: UcpBreakdownResponse
    effort: EffortEstimateResponse
    schedule: ScheduleEstimateResponse


class AnalysisAndCalculationResponse(BaseModel):
    """Response cho API gộp vừa extract vừa tính toán."""

    extraction: ExtractionResponse
    ucp: UcpBreakdownResponse
    effort: EffortEstimateResponse
    schedule: ScheduleEstimateResponse
