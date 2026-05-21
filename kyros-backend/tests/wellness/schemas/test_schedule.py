"""Tests for expand_schedule and Schedule validation."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from app.wellness.schemas.schedule import (
    IntervalSchedule,
    RecurringSchedule,
    expand_schedule,
)

IST = ZoneInfo("Asia/Kolkata")
ET = ZoneInfo("US/Eastern")


# ── helpers ───────────────────────────────────────────────────────────────────


def _recurring(
    times: list[str],
    days: list[str] | None = None,
    start: str = "2026-05-18",
    end: str | None = None,
    tz: str = "Asia/Kolkata",
) -> RecurringSchedule:
    return RecurringSchedule(
        type="recurring",
        times=times,
        days_of_week=days or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end) if end else None,
        timezone=tz,
    )


def _interval(
    interval_minutes: int = 120,
    window_start: str = "08:00",
    window_end: str = "22:00",
    days: list[str] | None = None,
    tz: str = "Asia/Kolkata",
) -> IntervalSchedule:
    return IntervalSchedule(
        type="interval",
        interval_minutes=interval_minutes,
        active_window={"start": window_start, "end": window_end},
        days_of_week=days or ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
        timezone=tz,
    )


# ── recurring schedule ────────────────────────────────────────────────────────


def test_recurring_48h_two_times_four_events() -> None:
    """Twice-daily IST schedule over 48 h produces exactly 4 fires."""
    schedule = _recurring(times=["08:00", "20:00"])
    from_dt = datetime(2026, 5, 18, 0, 0, tzinfo=IST)  # Monday midnight IST
    to_dt = from_dt + timedelta(hours=48)

    fires = expand_schedule(schedule, from_dt, to_dt)

    assert len(fires) == 4
    assert fires[0] == datetime(2026, 5, 18, 8, 0, tzinfo=IST)
    assert fires[1] == datetime(2026, 5, 18, 20, 0, tzinfo=IST)
    assert fires[2] == datetime(2026, 5, 19, 8, 0, tzinfo=IST)
    assert fires[3] == datetime(2026, 5, 19, 20, 0, tzinfo=IST)
    # All fires are timezone-aware
    assert all(f.tzinfo is not None for f in fires)


def test_recurring_across_ist_day_boundary() -> None:
    """Midnight fire in IST sits at the correct day."""
    schedule = _recurring(times=["00:00"])
    from_dt = datetime(2026, 5, 18, 22, 0, tzinfo=IST)
    to_dt = from_dt + timedelta(hours=4)

    fires = expand_schedule(schedule, from_dt, to_dt)

    assert len(fires) == 1
    assert fires[0] == datetime(2026, 5, 19, 0, 0, tzinfo=IST)


def test_recurring_end_date_respected() -> None:
    """Fires stop after end_date even when to_dt extends further."""
    schedule = _recurring(times=["08:00"], start="2026-05-18", end="2026-05-19")
    from_dt = datetime(2026, 5, 18, 0, 0, tzinfo=IST)
    to_dt = from_dt + timedelta(days=7)

    fires = expand_schedule(schedule, from_dt, to_dt)

    assert len(fires) == 2  # 18 May + 19 May only
    assert all(f.date() <= date(2026, 5, 19) for f in fires)


def test_recurring_from_dt_exclusive_start() -> None:
    """from_dt is inclusive — a fire exactly at from_dt is included."""
    schedule = _recurring(times=["08:00"])
    from_dt = datetime(2026, 5, 18, 8, 0, tzinfo=IST)
    to_dt = from_dt + timedelta(hours=1)

    fires = expand_schedule(schedule, from_dt, to_dt)

    assert len(fires) == 1
    assert fires[0] == from_dt


def test_recurring_to_dt_is_exclusive() -> None:
    """to_dt is exclusive — a fire exactly at to_dt is NOT included."""
    schedule = _recurring(times=["08:00"])
    from_dt = datetime(2026, 5, 18, 0, 0, tzinfo=IST)
    to_dt = datetime(2026, 5, 18, 8, 0, tzinfo=IST)

    fires = expand_schedule(schedule, from_dt, to_dt)

    assert len(fires) == 0


def test_recurring_days_of_week_filter() -> None:
    """Weekday-only schedule skips weekend fires."""
    schedule = _recurring(
        times=["08:00"],
        days=["mon", "tue", "wed", "thu", "fri"],
        start="2026-05-18",
    )
    # 2026-05-18 Mon … 2026-05-24 Sun
    from_dt = datetime(2026, 5, 18, 0, 0, tzinfo=IST)
    to_dt = from_dt + timedelta(days=7)

    fires = expand_schedule(schedule, from_dt, to_dt)

    assert len(fires) == 5
    fire_weekdays = [f.weekday() for f in fires]
    assert 5 not in fire_weekdays  # no Saturday
    assert 6 not in fire_weekdays  # no Sunday


# ── interval schedule ─────────────────────────────────────────────────────────


def test_interval_weekday_24h_8_events() -> None:
    """2-hour interval 08:00–22:00 on a weekday yields 8 events."""
    schedule = _interval(
        interval_minutes=120,
        window_start="08:00",
        window_end="22:00",
        days=["mon", "tue", "wed", "thu", "fri"],
    )
    # 2026-05-18 is Monday
    from_dt = datetime(2026, 5, 18, 0, 0, tzinfo=IST)
    to_dt = from_dt + timedelta(hours=24)

    fires = expand_schedule(schedule, from_dt, to_dt)

    assert len(fires) == 8
    fire_hours = [f.hour for f in fires]
    assert fire_hours == [8, 10, 12, 14, 16, 18, 20, 22]


def test_interval_weekend_zero_events() -> None:
    """Weekday-only interval on a Sunday produces no events."""
    schedule = _interval(
        days=["mon", "tue", "wed", "thu", "fri"],
    )
    # 2026-05-24 is Sunday
    from_dt = datetime(2026, 5, 24, 0, 0, tzinfo=IST)
    to_dt = from_dt + timedelta(hours=24)

    fires = expand_schedule(schedule, from_dt, to_dt)

    assert len(fires) == 0


def test_interval_active_window_boundaries() -> None:
    """Fires exactly at window start and end are both included."""
    schedule = _interval(interval_minutes=120, window_start="08:00", window_end="10:00")
    from_dt = datetime(2026, 5, 18, 0, 0, tzinfo=IST)
    to_dt = from_dt + timedelta(hours=24)

    fires = expand_schedule(schedule, from_dt, to_dt)

    fire_hours = [f.hour for f in fires]
    assert 8 in fire_hours
    assert 10 in fire_hours


# ── DST boundary (US/Eastern) ─────────────────────────────────────────────────


def test_interval_spring_forward_no_missing_fires() -> None:
    """
    US/Eastern spring forward 2026-03-08 02:00 EST → 03:00 EDT.
    Advancing by 60-min real-time increments should skip the non-existent
    02:xx hour — no fires land on hour=2.
    """
    # March 8, 2026 is Sunday
    schedule = _interval(
        interval_minutes=60,
        window_start="00:00",
        window_end="23:59",
        days=["sun"],
        tz="US/Eastern",
    )
    from_dt = datetime(2026, 3, 8, 1, 0, tzinfo=ET)
    to_dt = datetime(2026, 3, 8, 5, 0, tzinfo=ET)

    fires = expand_schedule(schedule, from_dt, to_dt)

    assert len(fires) >= 2
    fire_hours = [f.hour for f in fires]
    assert 2 not in fire_hours  # hour 2 doesn't exist on spring-forward day


def test_interval_fall_back_no_duplicate_fires() -> None:
    """
    US/Eastern fall back 2026-11-01 02:00 EDT → 01:00 EST.
    There are two real-time moments that display as '01:xx local'.
    Verify each fire is at a distinct UTC moment — no true duplicates.
    """
    # Nov 1, 2026 is Sunday
    schedule = _interval(
        interval_minutes=60,
        window_start="00:00",
        window_end="23:59",
        days=["sun"],
        tz="US/Eastern",
    )
    from_dt = datetime(2026, 11, 1, 0, 0, tzinfo=ET)
    to_dt = datetime(2026, 11, 1, 4, 0, tzinfo=ET)

    fires = expand_schedule(schedule, from_dt, to_dt)

    # Convert all to UTC and verify they are distinct
    utc_times = [f.astimezone(ZoneInfo("UTC")) for f in fires]
    assert len(utc_times) == len(set(utc_times))  # no duplicate UTC moments


# ── validation ────────────────────────────────────────────────────────────────


def test_empty_days_of_week_raises() -> None:
    with pytest.raises(ValidationError):
        RecurringSchedule(
            type="recurring",
            times=["08:00"],
            days_of_week=[],
            start_date=date.today(),
            timezone="Asia/Kolkata",
        )


def test_invalid_time_format_raises() -> None:
    with pytest.raises(ValidationError):
        RecurringSchedule(
            type="recurring",
            times=["25:00"],
            days_of_week=["mon"],
            start_date=date.today(),
            timezone="Asia/Kolkata",
        )


def test_invalid_timezone_raises() -> None:
    with pytest.raises(ValidationError):
        RecurringSchedule(
            type="recurring",
            times=["08:00"],
            days_of_week=["mon"],
            start_date=date.today(),
            timezone="Not/ATimezone",
        )


def test_active_window_end_before_start_raises() -> None:
    with pytest.raises(ValidationError):
        IntervalSchedule(
            type="interval",
            interval_minutes=60,
            active_window={"start": "22:00", "end": "08:00"},
            days_of_week=["mon"],
            timezone="Asia/Kolkata",
        )


def test_interval_minutes_zero_raises() -> None:
    with pytest.raises(ValidationError):
        IntervalSchedule(
            type="interval",
            interval_minutes=0,
            active_window={"start": "08:00", "end": "20:00"},
            days_of_week=["mon"],
            timezone="Asia/Kolkata",
        )
