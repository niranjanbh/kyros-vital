from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.exceptions import NotFoundError
from app.database import get_db
from app.shared.models.user import User
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem
from app.wellness.schemas.reminder import ReminderRead, ReminderUpdate, UpcomingFire
from app.wellness.services.upcoming import compute_upcoming

router = APIRouter(prefix="/v1/wellness/reminders", tags=["Wellness"])


# ── helpers ───────────────────────────────────────────────────────────────────


async def _get_reminder_or_404(
    reminder_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Reminder:
    """Fetch reminder and verify ownership via the parent tracked item."""
    result = await db.execute(
        select(Reminder)
        .join(TrackedItem, Reminder.tracked_item_id == TrackedItem.id)
        .where(Reminder.id == reminder_id, TrackedItem.user_id == user_id)
    )
    reminder = result.scalar_one_or_none()
    if reminder is None:
        raise NotFoundError("Reminder not found.")
    return reminder


# ── routes ────────────────────────────────────────────────────────────────────


@router.get("/upcoming", response_model=list[UpcomingFire])
async def get_upcoming(
    hours: Annotated[int, Query(ge=1, le=168)] = 24,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UpcomingFire]:
    return await compute_upcoming(current_user.id, hours, db)


@router.patch("/{reminder_id}", response_model=ReminderRead)
async def update_reminder(
    reminder_id: uuid.UUID,
    body: ReminderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Reminder:
    reminder = await _get_reminder_or_404(reminder_id, current_user.id, db)
    if body.schedule is not None:
        reminder.schedule = body.schedule.model_dump(mode="json")
    if body.message_template is not None:
        reminder.message_template = body.message_template
    if body.channels is not None:
        reminder.channels = body.channels
    if body.snooze_minutes is not None:
        reminder.snooze_minutes = body.snooze_minutes
    if body.taken_window_minutes is not None:
        reminder.taken_window_minutes = body.taken_window_minutes
    if body.active is not None:
        reminder.active = body.active
    db.add(reminder)
    await db.flush()
    await db.refresh(reminder)
    return reminder


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_reminder(
    reminder_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete: active → false. Row is kept for audit history."""
    reminder = await _get_reminder_or_404(reminder_id, current_user.id, db)
    reminder.active = False
    db.add(reminder)
    await db.flush()
