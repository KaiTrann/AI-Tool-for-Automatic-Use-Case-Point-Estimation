"""Các model request cho module tính UCP."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ComplexityLevel = Literal["simple", "average", "complex"]


class Actor(BaseModel):
    """Thông tin một actor dùng trong phép tính UCP."""

    name: str = Field(..., min_length=1, description="Tên actor")
    complexity: ComplexityLevel = Field(..., description="Mức độ phức tạp của actor")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Kiểm tra tên actor không được rỗng."""
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Tên actor không được để trống.")
        return cleaned_value


class UseCase(BaseModel):
    """Thông tin một use case dùng trong phép tính UCP."""

    name: str = Field(..., min_length=1, description="Tên use case")
    complexity: ComplexityLevel = Field(..., description="Mức độ phức tạp của use case")
    description: str | None = Field(default=None, description="Mô tả ngắn của use case")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Kiểm tra tên use case không được rỗng."""
        cleaned_value = value.strip()
        if not cleaned_value:
            raise ValueError("Tên use case không được để trống.")
        return cleaned_value


class UCPRequest(BaseModel):
    """Dữ liệu đầu vào cho bộ tính UCP."""

    actors: list[Actor] = Field(default_factory=list, description="Danh sách actor")
    use_cases: list[UseCase] = Field(default_factory=list, description="Danh sách use case")
    tcf: float = Field(..., gt=0, description="Hệ số kỹ thuật TCF")
    ecf: float = Field(..., gt=0, description="Hệ số môi trường ECF")
    productivity_factor: float = Field(..., gt=0, description="Hệ số năng suất")

    @model_validator(mode="after")
    def validate_non_empty_lists(self) -> "UCPRequest":
        """Bắt buộc phải có ít nhất một actor và một use case."""
        if not self.actors:
            raise ValueError("Phải có ít nhất một actor.")
        if not self.use_cases:
            raise ValueError("Phải có ít nhất một use case.")
        return self
