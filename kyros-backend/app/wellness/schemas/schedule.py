from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

_DOW_INDEX = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

DayOfWeek = Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _validate_time_str(v: str) -> str:
    if not _TIME_RE.match(v):
        raise ValueError(f"Invalid time {v!r} — expected HH:MM (00:00–23:59)")
    return v


def _validate_iana_tz(v: str) -> str:
    try:
        ZoneInfo(v)
    except (ZoneInfoNotFoundError, KeyError) as exc:
        raise ValueError(f"Unknown IANA timezone: {v!r}") from exc
    return v


class ActiveWindow(BaseModel):
    start: str
    end: str

    @field_validator("start", "end")
    @classmethod
    def _check_fmt(cls, v: str) -> str:
        return _validate_time_str(v)

    @model_validator(mode="after")
    def _check_end_after_start(self) -> ActiveWindow:
        sh, sm = map(int, self.start.split(":"))
        eh, em = map(int, self.end.split(":"))
        if (eh, em) <= (sh, sm):
            raise ValueError("active_window.end must be later than start")
        return self


class RecurringSchedule(BaseModel):
    type: Literal["recurring"]
    times: list[str]
    days_of_week: Annotated[list[DayOfWeek], Field(min_length=1)]
    start_date: date
    end_date: date | None = None
    timezone: str

    @field_validator("times")
    @classmethod
    def _check_times(cls, v: list[str]) -> list[str]:
        for t in v:
            _validate_time_str(t)
        return v

    @field_validator("timezone")
    @classmethod
    def _check_tz(cls, v: str) -> str:
        return _validate_iana_tz(v)


class IntervalSchedule(BaseModel):
    type: Literal["interval"]
    interval_minutes: Annotated[int, Field(gt=0, le=1440)]
    active_window: ActiveWindow
    days_of_week: Annotated[list[DayOfWeek], Field(min_length=1)]
    timezone: str

    @field_validator("timezone")
    @classmethod
    def _check_tz(cls, v: str) -> str:
        return _validate_iana_tz(v)


Schedule = Annotated[
    RecurringSchedule | IntervalSchedule,
    Field(discriminator="type"),
]


# ── schedule expansion ────────────────────────────────────────────────────────


def expand_schedule(
    schedule: RecurringSchedule | IntervalSchedule,
    from_dt: datetime,
    to_dt: datetime,
) -> list[datetime]:
    """
    Return tz-aware datetimes when the reminder fires in [from_dt, to_dt).
    Uses zoneinfo for DST-safe arithmetic.
    """
    if isinstance(schedule, RecurringSchedule):
        return _expand_recurring(schedule, from_dt, to_dt)
    return _expand_interval(schedule, from_dt, to_dt)


def _expand_recurring(
    schedule: RecurringSchedule,
    from_dt: datetime,
    to_dt: datetime,
) -> list[datetime]:
    tz = ZoneInfo(schedule.timezone)
    fires: list[datetime] = []
    allowed_dows = {_DOW_INDEX[d] for d in schedule.days_of_week}

    # Iterate dates in the schedule's local timezone
    current_date = from_dt.astimezone(tz).date()
    end_date = to_dt.astimezone(tz).date()

    while current_date <= end_date:
        if schedule.end_date and current_date > schedule.end_date:
            break
        if current_date >= schedule.start_date and current_date.weekday() in allowed_dows:
            for time_str in schedule.times:
                h, m = map(int, time_str.split(":"))
                fire_dt = datetime(
                    current_date.year,
                    current_date.month,
                    current_date.day,
                    h,
                    m,
                    tzinfo=tz,
                )
                if from_dt <= fire_dt < to_dt:
                    fires.append(fire_dt)
        current_date += timedelta(days=1)

    return sorted(fires)


def _expand_interval(
    schedule: IntervalSchedule,
    from_dt: datetime,
    to_dt: datetime,
) -> list[datetime]:
    tz = ZoneInfo(schedule.timezone)
    fires: list[datetime] = []
    allowed_dows = {_DOW_INDEX[d] for d in schedule.days_of_week}

    wsh, wsm = map(int, schedule.active_window.start.split(":"))
    weh, wem = map(int, schedule.active_window.end.split(":"))
    window_start = timedelta(hours=wsh, minutes=wsm)
    window_end = timedelta(hours=weh, minutes=wem)

    # Normalize to UTC so += timedelta is real-time arithmetic, not wall-clock.
    # ZoneInfo-aware datetimes use wall-clock addition which produces phantom
    # hours during spring-forward gaps.
    current_utc = from_dt.astimezone(UTC)
    to_utc = to_dt.astimezone(UTC)
    step = timedelta(minutes=schedule.interval_minutes)
    while current_utc < to_utc:
        local = current_utc.astimezone(tz)
        if local.weekday() in allowed_dows:
            local_tod = timedelta(hours=local.hour, minutes=local.minute)
            if window_start <= local_tod <= window_end:
                fires.append(local)
        current_utc += step

    return sorted(fires)
