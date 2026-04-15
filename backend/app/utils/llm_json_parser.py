"""Các hàm kiểm tra và chuẩn hóa JSON do bộ trích xuất trả về."""

import json

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.models.requests import ActorItem, UseCaseItem
from app.utils.parser import normalize_name

ALLOWED_COMPLEXITIES = {"simple", "average", "complex"}


class _StrictActorPayload(BaseModel):
    """Model kiểm tra dữ liệu actor ở dạng JSON thô."""

    name: str = Field(..., min_length=1)
    complexity: str

    @field_validator("name")
    @classmethod
    def normalize_actor_name(cls, value: str) -> str:
        """Chuẩn hóa tên actor và chặn chuỗi rỗng."""
        cleaned_value = normalize_name(value)
        if not cleaned_value:
            raise ValueError("Tên actor không được để trống.")
        return cleaned_value

    @field_validator("complexity")
    @classmethod
    def normalize_actor_complexity(cls, value: str) -> str:
        """Chuẩn hóa và kiểm tra complexity của actor."""
        normalized_value = value.strip().lower()
        if normalized_value not in ALLOWED_COMPLEXITIES:
            raise ValueError("Độ phức tạp của actor phải là simple, average hoặc complex.")
        return normalized_value


class _StrictUseCasePayload(BaseModel):
    """Model kiểm tra dữ liệu use case ở dạng JSON thô."""

    name: str = Field(..., min_length=1)
    complexity: str

    @field_validator("name")
    @classmethod
    def normalize_use_case_name(cls, value: str) -> str:
        """Chuẩn hóa tên use case và chặn chuỗi rỗng."""
        cleaned_value = normalize_name(value)
        if not cleaned_value:
            raise ValueError("Tên use case không được để trống.")
        return cleaned_value

    @field_validator("complexity")
    @classmethod
    def normalize_use_case_complexity(cls, value: str) -> str:
        """Chuẩn hóa và kiểm tra complexity của use case."""
        normalized_value = value.strip().lower()
        if normalized_value not in ALLOWED_COMPLEXITIES:
            raise ValueError("Độ phức tạp của use case phải là simple, average hoặc complex.")
        return normalized_value


class _StrictExtractionPayload(BaseModel):
    """Model kiểm tra JSON tổng thể do bộ trích xuất trả về."""

    actors: list[_StrictActorPayload] = Field(default_factory=list)
    use_cases: list[_StrictUseCasePayload] = Field(default_factory=list)


def parse_llm_extraction_json(raw_json: str) -> tuple[list[ActorItem], list[UseCaseItem]]:
    """Đọc JSON, kiểm tra cấu trúc và trả về model đã chuẩn hóa."""
    try:
        # Bước 1: parse chuỗi JSON thành object Python.
        payload = json.loads(raw_json)

        # Bước 2: dùng Pydantic để kiểm tra:
        # - có đủ key actors/use_cases hay chưa
        # - mỗi item có đúng field không
        # - complexity có đúng simple/average/complex hay không
        validated_payload = _StrictExtractionPayload.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as error:
        raise ValueError(f"JSON trích xuất không hợp lệ: {error}") from error

    # Bước 3: đổi về model dùng chung của project.
    actors = _deduplicate_actors(
        [
            ActorItem(name=item.name, complexity=item.complexity)
            for item in validated_payload.actors
        ]
    )
    use_cases = _deduplicate_use_cases(
        [
            UseCaseItem(name=item.name, complexity=item.complexity)
            for item in validated_payload.use_cases
        ]
    )

    # Kết quả sau parser đã:
    # - đúng schema
    # - complexity đúng format
    # - bỏ item trùng tên
    return actors, use_cases


def _deduplicate_actors(actors: list[ActorItem]) -> list[ActorItem]:
    """Xóa actor trùng tên sau khi đã chuẩn hóa."""
    seen: set[str] = set()
    unique_items: list[ActorItem] = []

    for actor in actors:
        key = actor.name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(actor)

    return unique_items


def _deduplicate_use_cases(use_cases: list[UseCaseItem]) -> list[UseCaseItem]:
    """Xóa use case trùng tên sau khi đã chuẩn hóa."""
    seen: set[str] = set()
    unique_items: list[UseCaseItem] = []

    for use_case in use_cases:
        key = use_case.name.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(use_case)

    return unique_items
