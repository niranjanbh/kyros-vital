from __future__ import annotations

import base64
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.exceptions import NotFoundError
from app.database import get_db
from app.shared.models.user import User
from app.wellness.models.measurement import Measurement
from app.wellness.schemas.measurement import (
    MeasurementCreate,
    MeasurementRead,
    MeasurementType,
    MeasurementUpdate,
)

router = APIRouter(prefix="/v1/wellness/measurements", tags=["Wellness"])

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


def _encode_cursor(measured_at: datetime, entry_id: uuid.UUID) -> str:
    raw = f"{measured_at.isoformat()}|{entry_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    ts_str, id_str = raw.split("|", 1)
    return datetime.fromisoformat(ts_str), uuid.UUID(id_str)


async def _get_measurement_or_404(
    measurement_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession,
) -> Measurement:
    result = await db.execute(
        select(Measurement).where(
            Measurement.id == measurement_id,
            Measurement.user_id == user_id,
        )
    )
    measurement = result.scalar_one_or_none()
    if measurement is None:
        raise NotFoundError("Measurement not found.")
    return measurement


@router.post("/", response_model=MeasurementRead, status_code=status.HTTP_201_CREATED)
async def create_measurement(
    body: MeasurementCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Measurement:
    measurement = Measurement(
        user_id=current_user.id,
        type=body.type,
        value=body.value,
        unit=body.unit,
        measured_at=body.measured_at,
        reference_range=body.reference_range,
        note=body.note,
    )
    db.add(measurement)
    await db.flush()
    await db.refresh(measurement)
    return measurement


@router.get("/", response_model=list[MeasurementRead])
async def list_measurements(
    type: Annotated[MeasurementType | None, Query()] = None,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=_MAX_LIMIT)] = _DEFAULT_LIMIT,
    cursor: Annotated[str | None, Query()] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Measurement]:
    stmt = (
        select(Measurement)
        .where(Measurement.user_id == current_user.id)
        .order_by(Measurement.measured_at.desc(), Measurement.id.desc())
        .limit(limit)
    )

    if type is not None:
        stmt = stmt.where(Measurement.type == type)
    if from_ is not None:
        stmt = stmt.where(Measurement.measured_at >= from_)
    if to is not None:
        stmt = stmt.where(Measurement.measured_at <= to)
    if cursor is not None:
        cursor_time, cursor_id = _decode_cursor(cursor)
        stmt = stmt.where(
            (Measurement.measured_at < cursor_time)
            | (
                (Measurement.measured_at == cursor_time)
                & (Measurement.id < cursor_id)
            )
        )

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{measurement_id}", response_model=MeasurementRead)
async def get_measurement(
    measurement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Measurement:
    return await _get_measurement_or_404(measurement_id, current_user.id, db)


@router.patch("/{measurement_id}", response_model=MeasurementRead)
async def update_measurement(
    measurement_id: uuid.UUID,
    body: MeasurementUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Measurement:
    measurement = await _get_measurement_or_404(measurement_id, current_user.id, db)
    if body.type is not None:
        measurement.type = body.type
    if body.value is not None:
        measurement.value = body.value
    if body.unit is not None:
        measurement.unit = body.unit
    if body.measured_at is not None:
        measurement.measured_at = body.measured_at
    if body.reference_range is not None:
        measurement.reference_range = body.reference_range
    if body.note is not None:
        measurement.note = body.note
    db.add(measurement)
    await db.flush()
    await db.refresh(measurement)
    return measurement


@router.delete("/{measurement_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_measurement(
    measurement_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Hard delete: user-corrected readings are not adherence history."""
    measurement = await _get_measurement_or_404(measurement_id, current_user.id, db)
    await db.delete(measurement)
    await db.flush()
