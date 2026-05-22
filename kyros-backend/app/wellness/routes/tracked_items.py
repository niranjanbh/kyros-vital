from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
from app.core.exceptions import NotFoundError
from app.database import get_db
from app.shared.models.user import User
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem
from app.wellness.schemas.reminder import ReminderCreate, ReminderRead
from app.wellness.schemas.tracked_item import (
    Category,
    Status,
    TrackedItemCreateRequest,
    TrackedItemRead,
    TrackedItemUpdate,
)

router = APIRouter(prefix="/v1/wellness/tracked-items", tags=["Wellness"])


# ── helpers ───────────────────────────────────────────────────────────────────


async def _get_item_or_404(
    item_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> TrackedItem:
    result = await db.execute(
        select(TrackedItem)
        .options(selectinload(TrackedItem.reminders))
        .where(TrackedItem.id == item_id, TrackedItem.user_id == user_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise NotFoundError("Tracked item not found.")
    return item


def _meta_dict(body_metadata: Any) -> dict[str, Any]:
    """Convert Pydantic metadata model or plain dict to a JSON-safe dict."""
    if hasattr(body_metadata, "model_dump"):
        result: dict[str, Any] = body_metadata.model_dump()
        return result
    return dict(body_metadata)


# ── tracked item CRUD ─────────────────────────────────────────────────────────


@router.get("/", response_model=list[TrackedItemRead])
async def list_tracked_items(
    category: Annotated[Category | None, Query()] = None,
    status: Annotated[Status | None, Query()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TrackedItem]:
    stmt = (
        select(TrackedItem)
        .options(selectinload(TrackedItem.reminders))
        .where(TrackedItem.user_id == current_user.id)
    )
    if category is not None:
        stmt = stmt.where(TrackedItem.category == category)
    if status is not None:
        stmt = stmt.where(TrackedItem.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/", response_model=TrackedItemRead, status_code=status.HTTP_201_CREATED)
async def create_tracked_item(
    body: TrackedItemCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedItem:
    item = TrackedItem(
        user_id=current_user.id,
        category=body.category,
        name=body.name,
        item_metadata=_meta_dict(body.metadata),
        start_date=body.start_date,
        end_date=body.end_date,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    # Load reminders relationship (empty at creation)
    await db.execute(
        select(TrackedItem)
        .options(selectinload(TrackedItem.reminders))
        .where(TrackedItem.id == item.id)
    )
    return item


@router.get("/{item_id}", response_model=TrackedItemRead)
async def get_tracked_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedItem:
    return await _get_item_or_404(item_id, current_user.id, db)


@router.patch("/{item_id}", response_model=TrackedItemRead)
async def update_tracked_item(
    item_id: uuid.UUID,
    body: TrackedItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TrackedItem:
    item = await _get_item_or_404(item_id, current_user.id, db)
    if body.name is not None:
        item.name = body.name
    if body.item_metadata is not None:
        item.item_metadata = body.item_metadata
    if body.status is not None:
        item.status = body.status
    if body.end_date is not None:
        item.end_date = body.end_date
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_tracked_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete: status → discontinued, all child reminders → inactive."""
    item = await _get_item_or_404(item_id, current_user.id, db)
    item.status = "discontinued"
    for reminder in item.reminders:
        reminder.active = False
    db.add(item)
    await db.flush()


# ── reminders sub-resource ────────────────────────────────────────────────────


@router.get("/{item_id}/reminders", response_model=list[ReminderRead])
async def list_item_reminders(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Reminder]:
    await _get_item_or_404(item_id, current_user.id, db)
    result = await db.execute(
        select(Reminder).where(Reminder.tracked_item_id == item_id)
    )
    return list(result.scalars().all())


@router.post(
    "/{item_id}/reminders",
    response_model=ReminderRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_item_reminder(
    item_id: uuid.UUID,
    body: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Reminder:
    await _get_item_or_404(item_id, current_user.id, db)
    reminder = Reminder(
        tracked_item_id=item_id,
        schedule=body.schedule.model_dump(mode="json"),
        message_template=body.message_template,
        channels=body.channels,
        snooze_minutes=body.snooze_minutes,
        taken_window_minutes=body.taken_window_minutes,
    )
    db.add(reminder)
    await db.flush()
    await db.refresh(reminder)
    return reminder
