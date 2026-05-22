"""Shared helpers for demo seed scripts."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
ALL_DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

_DAY_IDX: dict[str, int] = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6
}


def now_ist() -> datetime:
    return datetime.now(IST)


def days_ago(n: int) -> datetime:
    """Midnight IST, n days ago."""
    base = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    return base - timedelta(days=n)


def jittered_time(base: datetime, lo: int, hi: int) -> datetime:
    return base + timedelta(minutes=random.randint(lo, hi))


def weighted_action(weights: dict[str, float]) -> str | None:
    """
    weights: {'taken': 0.88, 'skipped': 0.08, 'missed': 0.04}
    Returns action string or None (for 'missed' = no log entry).
    """
    r = random.random()
    cumulative = 0.0
    for action, weight in weights.items():
        cumulative += weight
        if r < cumulative:
            return None if action == "missed" else action
    return None


def generate_fires_recurring(
    start_dt: datetime,
    end_dt: datetime,
    times: list[str],
    days_of_week: list[str],
) -> list[datetime]:
    """Return all fire datetimes for a recurring schedule, never in the future."""
    fires: list[datetime] = []
    allowed = {_DAY_IDX[d] for d in days_of_week}
    cutoff = min(end_dt, now_ist())
    day = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    while day <= cutoff:
        if day.weekday() in allowed:
            for t in times:
                h, m = map(int, t.split(":"))
                fire = day.replace(hour=h, minute=m, second=0, microsecond=0)
                if fire <= cutoff:
                    fires.append(fire)
        day += timedelta(days=1)
    return fires


def generate_fires_interval(
    start_dt: datetime,
    end_dt: datetime,
    interval_minutes: int,
    window_start: str,
    window_end: str,
    days_of_week: list[str],
) -> list[datetime]:
    """Return all interval fire datetimes, never in the future."""
    fires: list[datetime] = []
    allowed = {_DAY_IDX[d] for d in days_of_week}
    ws_h, ws_m = map(int, window_start.split(":"))
    we_h, we_m = map(int, window_end.split(":"))
    cutoff = min(end_dt, now_ist())
    day = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)

    while day <= cutoff:
        if day.weekday() in allowed:
            fire = day.replace(hour=ws_h, minute=ws_m, second=0, microsecond=0)
            window_end_dt = day.replace(hour=we_h, minute=we_m, second=0, microsecond=0)
            while fire <= window_end_dt and fire <= cutoff:
                fires.append(fire)
                fire += timedelta(minutes=interval_minutes)
        day += timedelta(days=1)
    return fires


def make_fire_key(reminder_id: uuid.UUID, fire_at: datetime) -> str:
    return f"{reminder_id}:{fire_at.isoformat()}"


def log_entry_dict(
    user_id: uuid.UUID,
    item_id: uuid.UUID,
    reminder_id: uuid.UUID,
    fire_key: str,
    action: str,
    occurred_at: datetime,
) -> dict[str, Any]:
    return {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "tracked_item_id": item_id,
        "reminder_id": reminder_id,
        "fire_key": fire_key,
        "action": action,
        "value": {},
        "occurred_at": occurred_at,
        "source": "demo_seed",
    }


def measurement_dict(
    user_id: uuid.UUID,
    mtype: str,
    value: float,
    unit: str,
    measured_at: datetime,
    reference_range: dict[str, Any] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "type": mtype,
        "value": Decimal(str(value)),
        "unit": unit,
        "measured_at": measured_at,
        "reference_range": reference_range,
        "note": note,
        "source": "demo_seed",
    }


def parsed_test(
    name: str,
    value: str,
    unit: str,
    ref_low: float | None,
    ref_high: float | None,
    flag: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "unit": unit,
        "ref_low": ref_low,
        "ref_high": ref_high,
        "flag": flag,
    }
