from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

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
        for fire_at in expand_schedule(schedule, now, to_dt):
            fire_key = f"{reminder.id}:{fire_at.isoformat()}"
            body = reminder.message_template.format_map(_SafeDict(item.item_metadata))
            fires.append(
                UpcomingFire(
                    reminder_id=reminder.id,
                    tracked_item_id=item.id,
                    fire_at=fire_at,
                    fire_key=fire_key,
                    payload={
                        "title": _CATEGORY_TITLES.get(item.category, "Reminder"),
                        "body": body,
                        "category": item.category,
                        "actions": _CATEGORY_ACTIONS.get(item.category, ["acknowledged"]),
                    },
                )
            )

    fires.sort(key=lambda f: f.fire_at)
    return fires
