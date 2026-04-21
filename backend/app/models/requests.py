"""Các model request chính của backend."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

ComplexityLevel = Literal["simple", "average", "complex"]
LlmMode = Literal["mock", "placeholder"]


class ActorItem(BaseModel):
    """Thông tin một actor đã được trích xuất hoặc duyệt lại."""

    name: str = Field(..., examples=["Admin"])
    complexity: ComplexityLevel = Field(default="average")


class UseCaseItem(BaseModel):
    """Thông tin một use case đã được trích xuất hoặc duyệt lại."""

    name: str = Field(..., examples=["Generate estimation report"])
    complexity: ComplexityLevel = Field(default="average")
    description: str | None = Field(default=None)


class NormalizedUseCaseDocument(BaseModel):
    """Schema chuẩn nội bộ cho một Use Case Specification sau khi parse và normalize.

    Toàn bộ tài liệu use case có cấu trúc sẽ được đưa về đúng schema này trước khi:
    - phân loại actor
    - đếm transaction
    - tính complexity của use case
    - tính UCP
    """

    use_case_id: str | None = Field(default=None)
    use_case_name: str = Field(..., min_length=1)
    actors: list[str] = Field(default_factory=list)
    primary_actor: str | None = Field(default=None)
    secondary_actors: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None)
    goal: str | None = Field(default=None)
    trigger: str | None = Field(default=None)
    preconditions: str | None = Field(default=None)
    postconditions: str | None = Field(default=None)
    functional_requirement: str | None = Field(default=None)
    main_flow_steps: list[str] = Field(default_factory=list)
    alternative_flow_steps: list[str] = Field(default_factory=list)
    exception_flow_steps: list[str] = Field(default_factory=list)
    main_success_scenario: list[str] = Field(default_factory=list)
    alternative_flows: list[str] = Field(default_factory=list)
    exception_flows: list[str] = Field(default_factory=list)
    priority: str | None = Field(default=None)
    business_rules: str | None = Field(default=None)
    source_template_type: str | None = Field(default=None)
    notes: str | None = Field(default=None)


class ExtractRequest(BaseModel):
    """Model request sau khi đã gộp text nhập tay và text từ file."""

    source_text: str | None = Field(default=None)
    file_name: str | None = Field(default=None)
    file_text: str | None = Field(default=None)
    llm_mode: LlmMode = Field(default="mock")

    @field_validator("source_text", "file_text")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        """Xóa khoảng trắng thừa để chuỗi rỗng không đi tiếp trong luồng xử lý."""
        if value is None:
            return None
        cleaned_value = value.strip()
        return cleaned_value or None


class AnalyzeAndCalculateRequest(ExtractRequest):
    """Model request cho API gộp vừa trích xuất vừa tính toán."""

    technical_complexity_factor: float = Field(default=1.0, ge=0.5, le=1.5)
    environmental_complexity_factor: float = Field(default=1.0, ge=0.5, le=1.5)
    productivity_factor: float = Field(default=20.0, ge=1.0)
    team_size: int = Field(default=3, ge=1)


class UcpCalculateRequest(BaseModel):
    """Model request cho API tính UCP sau khi đã có actor và use case."""

    actors: list[ActorItem] = Field(default_factory=list)
    use_cases: list[UseCaseItem] = Field(default_factory=list)
    technical_complexity_factor: float = Field(default=1.0, ge=0.5, le=1.5)
    environmental_complexity_factor: float = Field(default=1.0, ge=0.5, le=1.5)
    productivity_factor: float = Field(default=20.0, ge=1.0)
    team_size: int = Field(default=3, ge=1)
