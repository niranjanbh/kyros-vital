from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.error_log import ErrorLog

PAGE_SIZE = 50


async def list_errors(
    db: AsyncSession,
    *,
    page: int = 1,
    status_code: int | None = None,
    path_contains: str | None = None,
    error_type: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[list[ErrorLog], int]:
    stmt = select(ErrorLog)

    if status_code is not None:
        stmt = stmt.where(ErrorLog.status_code == status_code)
    if path_contains:
        stmt = stmt.where(ErrorLog.path.ilike(f"%{path_contains}%"))
    if error_type:
        stmt = stmt.where(ErrorLog.error_type.ilike(f"%{error_type}%"))
    if from_date:
        stmt = stmt.where(ErrorLog.occurred_at >= datetime(from_date.year, from_date.month, from_date.day, tzinfo=UTC))
    if to_date:
        end = datetime(to_date.year, to_date.month, to_date.day, tzinfo=UTC) + timedelta(days=1)
        stmt = stmt.where(ErrorLog.occurred_at < end)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(ErrorLog.occurred_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    rows = await db.execute(stmt)
    return list(rows.scalars().all()), total


async def get_error(db: AsyncSession, error_id: str) -> ErrorLog | None:
    from uuid import UUID
    try:
        uid = UUID(error_id)
    except ValueError:
        return None
    row = await db.execute(select(ErrorLog).where(ErrorLog.id == uid))
    return row.scalar_one_or_none()


async def error_summary_last_24h(db: AsyncSession) -> dict[str, int]:
    cutoff = datetime.now(tz=UTC) - timedelta(hours=24)
    rows = await db.execute(
        select(ErrorLog.status_code, func.count())
        .where(ErrorLog.occurred_at >= cutoff)
        .group_by(ErrorLog.status_code)
        .order_by(ErrorLog.status_code)
    )
    return {str(code): count for code, count in rows.all()}


async def delete_old_errors(db: AsyncSession, days: int = 30) -> int:
    from sqlalchemy import delete
    cutoff = datetime.now(tz=UTC) - timedelta(days=days)
    result = await db.execute(delete(ErrorLog).where(ErrorLog.occurred_at < cutoff))
    await db.commit()
    return result.rowcount  # type: ignore[return-value]
