"""Service tính effort từ giá trị UCP."""

from app.models.responses import EffortEstimateResponse


def estimate_effort(ucp: float, productivity_factor: float) -> EffortEstimateResponse:
    """Tính effort theo công thức đơn giản: UCP * productivity factor."""
    hours = round(ucp * productivity_factor, 2)
    person_days = round(hours / 8, 2)
    return EffortEstimateResponse(
        hours=hours,
        person_days=person_days,
        productivity_factor=productivity_factor,
    )
