"""Dashboard metrics — all queries in one place, unit-testable, 30-second in-process cache."""

import shutil
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinic.models.consultation import Consultation
from app.shared.models.audit_log import AuditLog
from app.shared.models.user import User
from app.wellness.models.log_entry import LogEntry
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem

_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 30.0  # seconds


def _get_cached(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _set_cached(key: str, value: Any) -> None:
    _cache[key] = (time.monotonic(), value)


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


# ── User metrics ────────────────────────────────────────────────────────────

async def count_total_users(db: AsyncSession) -> int:
    row = await db.execute(select(func.count()).select_from(User))
    return row.scalar_one()


async def count_active_users(db: AsyncSession, days: int) -> int:
    cutoff = _now_utc() - timedelta(days=days)
    row = await db.execute(
        select(func.count(func.distinct(AuditLog.user_id)))
        .where(AuditLog.actor_type == "user")
        .where(AuditLog.occurred_at >= cutoff)
    )
    return row.scalar_one()


async def count_new_users(db: AsyncSession, days: int) -> int:
    cutoff = _now_utc() - timedelta(days=days)
    row = await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= cutoff)
    )
    return row.scalar_one()


async def count_users_with_email(db: AsyncSession) -> int:
    row = await db.execute(
        select(func.count()).select_from(User).where(User.email.isnot(None))
    )
    return row.scalar_one()


# ── Tracked item metrics ─────────────────────────────────────────────────────

async def items_by_status(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(
        select(TrackedItem.status, func.count()).group_by(TrackedItem.status)
    )
    return dict(rows.all())


async def items_by_category(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(
        select(TrackedItem.category, func.count()).group_by(TrackedItem.category)
    )
    return dict(rows.all())


async def count_items_created_last_n_days(db: AsyncSession, days: int) -> int:
    cutoff = _now_utc() - timedelta(days=days)
    row = await db.execute(
        select(func.count()).select_from(TrackedItem).where(TrackedItem.created_at >= cutoff)
    )
    return row.scalar_one()


async def count_items_discontinued_last_n_days(db: AsyncSession, days: int) -> int:
    cutoff = _now_utc() - timedelta(days=days)
    row = await db.execute(
        select(func.count())
        .select_from(TrackedItem)
        .where(TrackedItem.status == "discontinued")
        .where(TrackedItem.updated_at >= cutoff)
    )
    return row.scalar_one()


# ── Reminder & adherence metrics ─────────────────────────────────────────────

async def count_reminders(db: AsyncSession) -> tuple[int, int]:
    """Returns (total, active)."""
    total_row = await db.execute(select(func.count()).select_from(Reminder))
    active_row = await db.execute(
        select(func.count()).select_from(Reminder).where(Reminder.active.is_(True))
    )
    return total_row.scalar_one(), active_row.scalar_one()


async def adherence_last_7_days(db: AsyncSession) -> dict[str, Any]:
    """Taken/(taken+skipped) from log entries in last 7 days."""
    cutoff = _now_utc() - timedelta(days=7)
    rows = await db.execute(
        select(LogEntry.action, func.count())
        .where(LogEntry.occurred_at >= cutoff)
        .group_by(LogEntry.action)
    )
    counts: dict[str, int] = dict(rows.all())
    taken = counts.get("taken", 0)
    skipped = counts.get("skipped", 0)
    denominator = taken + skipped
    rate: float | None = (taken / denominator) if denominator > 0 else None
    return {"taken": taken, "skipped": skipped, "rate": rate}


# ── Consultation metrics ──────────────────────────────────────────────────────

async def consultations_last_n_days(db: AsyncSession, days: int) -> int:
    cutoff = _now_utc() - timedelta(days=days)
    row = await db.execute(
        select(func.count())
        .select_from(Consultation)
        .where(Consultation.created_at >= cutoff)
    )
    return row.scalar_one()


async def consultations_by_status(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(
        select(Consultation.status, func.count()).group_by(Consultation.status)
    )
    return dict(rows.all())


async def consultations_upcoming(db: AsyncSession, hours: int = 48) -> int:
    now = _now_utc()
    cutoff = now + timedelta(hours=hours)
    row = await db.execute(
        select(func.count())
        .select_from(Consultation)
        .where(Consultation.status == "scheduled")
        .where(Consultation.scheduled_at >= now)
        .where(Consultation.scheduled_at < cutoff)
    )
    return row.scalar_one()


async def revenue_last_30_days(db: AsyncSession) -> int:
    cutoff = _now_utc() - timedelta(days=30)
    row = await db.execute(
        select(func.coalesce(func.sum(Consultation.fee_paid_paise), 0))
        .where(Consultation.status == "completed")
        .where(Consultation.completed_at >= cutoff)
    )
    raw = row.scalar_one()
    # coalesce guarantees non-null but may be Decimal from Postgres SUM
    return int(raw) if raw is not None else 0


# ── System metrics ────────────────────────────────────────────────────────────

async def db_alive(db: AsyncSession) -> bool:
    try:
        async with db.begin_nested():  # SAVEPOINT — prevents abort of outer transaction
            await db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def disk_usage_gb() -> dict[str, float]:
    try:
        usage = shutil.disk_usage("/")
        return {
            "total_gb": round(usage.total / 1e9, 1),
            "used_gb": round(usage.used / 1e9, 1),
            "free_gb": round(usage.free / 1e9, 1),
            "used_pct": round(usage.used / usage.total * 100, 1),
        }
    except Exception:
        return {}


async def last_alembic_version(db: AsyncSession) -> str:
    # alembic_version doesn't exist in test DBs created via create_all — use SAVEPOINT
    try:
        async with db.begin_nested():
            row = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            result = row.scalar_one_or_none()
            return str(result) if result else "unknown"
    except Exception:
        return "unknown"


# ── Composite dashboard bundle ────────────────────────────────────────────────

async def get_dashboard_metrics(db: AsyncSession) -> dict[str, Any]:
    """Fetch all dashboard metrics with a 30-second in-process cache."""
    cached = _get_cached("dashboard")
    if cached is not None:
        return cached  # type: ignore[no-any-return]

    items_status = await items_by_status(db)
    items_cat = await items_by_category(db)
    total_reminders, active_reminders = await count_reminders(db)
    adherence = await adherence_last_7_days(db)
    consult_status = await consultations_by_status(db)
    revenue_paise = await revenue_last_30_days(db)

    metrics: dict[str, Any] = {
        # Block 1 — Users
        "users": {
            "total": await count_total_users(db),
            "active_7d": await count_active_users(db, 7),
            "active_30d": await count_active_users(db, 30),
            "new_7d": await count_new_users(db, 7),
            "with_email": await count_users_with_email(db),
        },
        # Block 2 — Tracked items (key avoids dict.items() collision in templates)
        "tracked_items": {
            "by_status": items_status,
            "by_category": items_cat,
            "created_7d": await count_items_created_last_n_days(db, 7),
            "discontinued_7d": await count_items_discontinued_last_n_days(db, 7),
        },
        # Block 3 — Reminders
        "reminders": {
            "total": total_reminders,
            "active": active_reminders,
            "adherence_7d": adherence,
        },
        # Block 4 — Consultations
        "consultations": {
            "last_7d": await consultations_last_n_days(db, 7),
            "by_status": consult_status,
            "upcoming_48h": await consultations_upcoming(db, 48),
            "revenue_30d_paise": revenue_paise,
            "revenue_30d_rupees": revenue_paise / 100,
        },
        # Block 5 — System
        "system": {
            "db_ok": await db_alive(db),
            "disk": disk_usage_gb(),
            "alembic_version": await last_alembic_version(db),
        },
    }

    _set_cached("dashboard", metrics)
    return metrics


async def get_recent_audit(db: AsyncSession, limit: int = 20) -> list[AuditLog]:
    rows = await db.execute(
        select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(limit)
    )
    return list(rows.scalars().all())
