"""Các model response cho module tính UCP."""

from pydantic import BaseModel, Field


class UCPResponse(BaseModel):
    """Kết quả cuối cùng của bộ tính UCP."""

    uaw: float = Field(..., description="Tổng trọng số actor")
    uucw: float = Field(..., description="Tổng trọng số use case")
    uucp: float = Field(..., description="Tổng điểm use case chưa hiệu chỉnh")
    ucp: float = Field(..., description="Tổng điểm use case đã hiệu chỉnh")
    effort_estimation: float = Field(..., description="Ước lượng effort")
