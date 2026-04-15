"""API kiểm tra backend có đang hoạt động hay không."""

from fastapi import APIRouter

from app.models.responses import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Trả về trạng thái đơn giản để frontend kiểm tra kết nối."""
    return HealthResponse(status="ok", service="backend-uoc-luong-ucp")
