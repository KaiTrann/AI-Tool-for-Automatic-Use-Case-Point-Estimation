"""Service tính lịch trình dự kiến từ effort."""

import math

from app.models.responses import ScheduleEstimateResponse



def estimate_schedule(hours: float, team_size: int) -> ScheduleEstimateResponse:
    """Ước lượng số tháng theo công thức:

    schedule = effort_hours / (team_size * 160)
    """
    effective_team_size = max(team_size, 1)
    months = round(hours / (effective_team_size * 160), 2)
    sprint_count = max(math.ceil(months / 0.5), 1)
    return ScheduleEstimateResponse(
        months=months,
        recommended_team_size=effective_team_size,
        sprint_count=sprint_count,
    )
