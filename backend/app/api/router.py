"""Router trung tâm để gom tất cả API của ứng dụng."""

from fastapi import APIRouter

from app.api.routes.analysis import router as analysis_router
from app.api.routes.health import router as health_router

# Router tổng để `main.py` chỉ cần include một lần.
api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(analysis_router, tags=["analysis"])
