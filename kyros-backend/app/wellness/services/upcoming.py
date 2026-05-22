from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import TypeAdapter
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.user import User
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem
from app.wellness.schemas.reminder import UpcomingFire
from app.wellness.schemas.schedule import Schedule, expand_schedule

_schedule_adapter: TypeAdapter[Any] = TypeAdapter(Schedule)

_CATEGORY_TITLES: dict[str, str] = {
    "medication": "Medication",
    "water": "Hydration",
    "meal": "Meal",
    "workout": "Workout",
    "vital_check": "Reminder",
    "custom": "Reminder",
}

_CATEGORY_ACTIONS: dict[str, list[str]] = {
    "medication": ["taken", "skipped", "snooze_15"],
    "water": ["logged_value", "skipped", "snooze_15"],
    "meal": ["taken", "skipped", "snooze_15"],
    "workout": ["taken", "skipped", "snooze_30"],
    "vital_check": ["logged_value", "skipped", "snooze_15"],
    "custom": ["acknowledged", "snooze_15"],
}


class _SafeDict(dict):  # type: ignore[type-arg]
    """Missing keys render as the literal key name — never crash on unknown {tokens}."""

    def __missing__(self, key: str) -> str:
        return key


async def compute_upcoming(
    user_id: uuid.UUID,
    hours: int,
    db: AsyncSession,
) -> list[UpcomingFire]:
    now = datetime.now(tz=UTC)
    to_dt = now + timedelta(hours=hours)
    today = now.date()

    # Look back to midnight of today in the user's local timezone so that
    # already-past fires remain visible for the rest of the day. Without this,
    # a fire that has passed its scheduled time disappears from the list and
    # gets replaced by tomorrow's occurrence — making a just-logged card look
    # like it reverted to pending after the cache invalidates.
    user_row = await db.execute(
        select(User.timezone).where(User.id == user_id)
    )
    tz_str = user_row.scalar_one_or_none() or "UTC"
    try:
        user_tz = ZoneInfo(tz_str)
    except (ZoneInfoNotFoundError, KeyError):
        user_tz = UTC

    today_local = now.astimezone(user_tz).date()
    from_dt = datetime(
        today_local.year, today_local.month, today_local.day, tzinfo=user_tz
    ).astimezone(UTC)

    stmt = (
        select(Reminder, TrackedItem)
        .join(TrackedItem, Reminder.tracked_item_id == TrackedItem.id)
        .where(
            TrackedItem.user_id == user_id,
            TrackedItem.status == "active",
            Reminder.active.is_(True),
            TrackedItem.start_date <= today,
            or_(TrackedItem.end_date.is_(None), TrackedItem.end_date >= today),
        )
    )
    result = await db.execute(stmt)

    fires: list[UpcomingFire] = []
    for reminder, item in result.all():
        schedule = _schedule_adapter.validate_python(reminder.schedule)
        # Don't show fires that predate the reminder's creation — if a reminder
        # is created at 3 PM for an 8 AM schedule, the 8 AM fire shouldn't appear.
        reminder_created_utc = reminder.created_at.astimezone(UTC)
        effective_from = max(from_dt, reminder_created_utc)
        for fire_at in expand_schedule(schedule, effective_from, to_dt):
            fire_key = f"{reminder.id}:{fire_at.isoformat()}"
            body = reminder.message_template.format_map(_SafeDict(item.item_metadata))
            fires.append(
                UpcomingFire(
                    reminder_id=reminder.id,
                    tracked_item_id=item.id,
                    fire_at=fire_at,
                    fire_key=fire_key,
                    snooze_minutes=reminder.snooze_minutes,
                    taken_window_minutes=reminder.taken_window_minutes,
                    payload={
                        "title": _CATEGORY_TITLES.get(item.category, "Reminder"),
                        "body": body,
                        "category": item.category,
                        "actions": _CATEGORY_ACTIONS.get(item.category, ["acknowledged"]),
                        "snooze_minutes": reminder.snooze_minutes,
                        "taken_window_minutes": reminder.taken_window_minutes,
                    },
                )
            )

    fires.sort(key=lambda f: f.fire_at)
    return fires
