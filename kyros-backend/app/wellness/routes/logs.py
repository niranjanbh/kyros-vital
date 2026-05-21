from __future__ import annotations

import base64
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.exceptions import AppValidationError, NotFoundError
from app.database import get_db
from app.shared.models.user import User
from app.wellness.models.log_entry import LogEntry
from app.wellness.schemas.log_entry import LogEntryCreate, LogEntryRead

router = APIRouter(prefix="/v1/wellness/logs", tags=["Wellness"])

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _encode_cursor(occurred_at: datetime, entry_id: uuid.UUID) -> str:
    raw = f"{occurred_at.isoformat()}|{entry_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_str, id_str = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), uuid.UUID(id_str)


@router.post("/", response_model=LogEntryRead, status_code=status.HTTP_201_CREATED)
async def create_log_entry(
    body: LogEntryCreate,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LogEntryRead:
    values: dict = {
        "user_id": current_user.id,
        "tracked_item_id": body.tracked_item_id,
        "action": body.action,
        "occurred_at": body.occurred_at,
        "reminder_id": body.reminder_id,
        "fire_key": body.fire_key,
        "value": body.value,
        "note": body.note,
    }

    if body.fire_key is not None:
        # INSERT ... ON CONFLICT (fire_key) DO NOTHING RETURNING *
        stmt = (
            pg_insert(LogEntry)
            .values(**values)
            .on_conflict_do_nothing()
            .returning(*LogEntry.__table__.c)
        )
        try:
            async with db.begin_nested():
                result = await db.execute(stmt)
        except IntegrityError:
            # Race condition or FK violation; fall through to re-fetch
            row = None
        else:
            row = result.mappings().first()

        if row is None:
            # Conflict (existing fire_key) or race — return existing row
            existing = await db.execute(
                select(LogEntry).where(
                    LogEntry.fire_key == body.fire_key,
                    LogEntry.user_id == current_user.id,
                )
            )
            entry = existing.scalar_one_or_none()
            if entry is None:
                # fire_key conflict from a different user, or FK violation
                raise AppValidationError(
                    "Could not create log entry: conflict or invalid reference."
                )
            response.status_code = status.HTTP_200_OK
            return LogEntryRead.model_validate(entry)

        return LogEntryRead.model_validate(dict(row))

    # No fire_key: plain insert
    try:
        async with db.begin_nested():
            entry = LogEntry(**values)
            db.add(entry)
            await db.flush()
    except IntegrityError as exc:
        raise NotFoundError("Referenced tracked item not found.") from exc

    await db.refresh(entry)
    return LogEntryRead.model_validate(entry)


@router.get("/", response_model=list[LogEntryRead])
async def list_log_entries(
    tracked_item_id: Annotated[uuid.UUID | None, Query()] = None,
    action: Annotated[str | None, Query()] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=_MAX_LIMIT)] = _DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LogEntry]:
    stmt = (
        select(LogEntry)
        .where(LogEntry.user_id == current_user.id)
        .order_by(LogEntry.occurred_at.desc(), LogEntry.id.desc())
        .limit(limit)
    )

    if tracked_item_id is not None:
        stmt = stmt.where(LogEntry.tracked_item_id == tracked_item_id)
    if action is not None:
        stmt = stmt.where(LogEntry.action == action)
    if from_ is not None:
        stmt = stmt.where(LogEntry.occurred_at >= from_)
    if to is not None:
        stmt = stmt.where(LogEntry.occurred_at <= to)
    if cursor is not None:
        cursor_time, cursor_id = _decode_cursor(cursor)
        stmt = stmt.where(
            (LogEntry.occurred_at < cursor_time)
            | (
                (LogEntry.occurred_at == cursor_time)
                & (LogEntry.id < cursor_id)
            )
        )

    result = await db.execute(stmt)
    return list(result.scalars().all())
