"""Service tính lịch trình dự kiến từ effort."""

import math
from decimal import Decimal, ROUND_HALF_UP

from app.models.responses import ScheduleEstimateResponse


def estimate_schedule(hours: float, team_size: int) -> ScheduleEstimateResponse:
    """Ước lượng số tháng theo công thức:

    schedule = effort_hours / (team_size * 160)
    """
    effective_team_size = max(team_size, 1)
    raw_months = hours / (effective_team_size * 160)

    # Dùng ROUND_HALF_UP để dễ giải thích trong báo cáo học thuật.
    # Ví dụ 3.125 -> 3.13 thay vì 3.12 theo banker rounding của Python.
    months = float(
        Decimal(str(raw_months)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )

    sprint_count = max(math.ceil(months / 0.5), 1)
    return ScheduleEstimateResponse(
        months=months,
        recommended_team_size=effective_team_size,
        sprint_count=sprint_count,
    )
