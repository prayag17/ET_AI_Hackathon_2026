"""
Forecast endpoint — returns AQI snapshots for every hour from T+0 to T+72.

Since the demo data has a single static snapshot (grid_pollution_demo.csv),
we synthesise hourly variation using realistic diurnal and day-over-day
patterns so the time slider has something meaningful to show.

Pattern applied per cell per hour offset:
  • diurnal factor  : rush-hour peaks at 08:00 and 19:00, valley at 04:00
  • day penalty     : AQI drifts +4 % on day-2 and +8 % on day-3 to show
                      a worsening forecast (typical for a hackathon demo)
  • spatial noise   : seeded from grid_id so each cell varies independently
                      and the pattern is deterministic / reproducible
"""

import csv
import math
import hashlib
from pathlib import Path

from fastapi import APIRouter

router = APIRouter()

POLLUTION_CSV = (
    Path(__file__).resolve().parents[2] / "ai_model" / "data" / "grid_pollution_demo.csv"
)

# Diurnal shape: 24 multipliers (index = hour of day)
# Peak morning rush ~08:00, peak evening rush ~19:00, trough ~04:00
_DIURNAL = [
    0.82, 0.78, 0.75, 0.73, 0.72, 0.76,   # 00-05 night / early morning
    0.85, 0.97, 1.10, 1.08, 1.04, 1.02,   # 06-11 morning ramp-up
    1.00, 1.01, 1.03, 1.05, 1.07, 1.09,   # 12-17 afternoon build
    1.13, 1.15, 1.11, 1.05, 0.96, 0.88,   # 18-23 evening peak & decay
]

# Day-over-day drift (index 0 = T+0 … T+23, index 1 = T+24…47, index 2 = T+48…71)
_DAY_DRIFT = [1.00, 1.04, 1.08]

# Base reference hour for the demo snapshot
_BASE_HOUR = 9  # pretend snapshot was taken at 09:00


def _cell_noise(grid_id: str, hour_offset: int) -> float:
    """Deterministic ±8 % noise seeded from (grid_id, hour_offset)."""
    seed = hashlib.md5(f"{grid_id}-{hour_offset}".encode()).digest()
    # map first byte [0,255] -> [-0.08, +0.08]
    return (seed[0] / 255.0 - 0.5) * 0.16


def _aqi_at_offset(base_aqi: float, grid_id: str, offset_hours: int) -> float:
    """Apply diurnal + drift + spatial noise to a base AQI value."""
    day = offset_hours // 24
    hour = (_BASE_HOUR + offset_hours) % 24
    factor = _DIURNAL[hour] * _DAY_DRIFT[min(day, 2)]
    noise = _cell_noise(grid_id, offset_hours)
    return round(max(0.0, base_aqi * factor * (1 + noise)), 1)


@router.get("/getForecast", tags=["Maps"])
async def get_forecast():
    """
    Returns a 73-element array (T+0 … T+72) where each element is:
        { "offset_hours": int, "values": { "AHM-XXXX": aqi_float, … } }
    """
    with POLLUTION_CSV.open("r", encoding="utf-8") as f:
        base_rows = list(csv.DictReader(f))

    base: dict[str, float] = {r["grid_id"]: float(r["value"]) for r in base_rows}
    base_datetime: str = base_rows[0]["datetime"]

    snapshots = []
    for h in range(73):  # 0 … 72 inclusive
        snapshots.append(
            {
                "offset_hours": h,
                "base_datetime": base_datetime,
                "values": {gid: _aqi_at_offset(aqi, gid, h) for gid, aqi in base.items()},
            }
        )

    return {"base_datetime": base_datetime, "snapshots": snapshots}
