"""Tests for scripts/seed_demo.py — safety guards, idempotency, and data quality."""

from __future__ import annotations

import os
from decimal import Decimal
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.user import User
from app.wellness.models.log_entry import LogEntry
from app.wellness.models.measurement import Measurement
from app.wellness.models.tracked_item import TrackedItem
from scripts.seed_demo import _safety_checks, seed_all


# ── helpers ───────────────────────────────────────────────────────────────────


async def _user_id(db: AsyncSession, device_id: str):
    r = await db.execute(select(User.id).where(User.device_id == device_id))
    return r.scalar_one_or_none()


async def _count_logs(db: AsyncSession, user_id, action: str | None = None):
    q = select(func.count()).select_from(LogEntry).where(LogEntry.user_id == user_id)
    if action:
        q = q.where(LogEntry.action == action)
    r = await db.execute(q)
    return r.scalar_one()


# ── tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_safety_production_guard(db: AsyncSession) -> None:
    """seed_all() must refuse to run when ENV=production."""
    with patch.dict(os.environ, {"ENV": "production"}):
        with pytest.raises(RuntimeError, match="production"):
            await seed_all()


@pytest.mark.asyncio
async def test_safety_user_count_guard(db: AsyncSession) -> None:
    """seed_all() must refuse when non-demo user count exceeds threshold."""
    # Insert 51 fake non-demo users directly
    fake_users = [
        User(device_id=f"real-user-{i:04d}", name=f"User{i}", timezone="Asia/Kolkata")
        for i in range(51)
    ]
    for u in fake_users:
        db.add(u)
    await db.flush()

    with pytest.raises(RuntimeError, match="Safety guard"):
        await _safety_checks(db)

    await db.rollback()


@pytest.mark.asyncio
async def test_idempotent(db: AsyncSession) -> None:
    """Running seed_all() twice yields the same row counts (wipe + re-seed)."""
    stats1 = await seed_all()
    db.expire_all()

    stats2 = await seed_all()

    assert set(stats1.keys()) == set(stats2.keys())
    for name in stats1:
        assert stats1[name]["tracked_items"] == stats2[name]["tracked_items"], (
            f"{name} tracked_items mismatch: {stats1[name]['tracked_items']} vs "
            f"{stats2[name]['tracked_items']}"
        )
        assert stats1[name]["log_entries"] == stats2[name]["log_entries"], (
            f"{name} log_entries mismatch"
        )
        assert stats1[name]["measurements"] == stats2[name]["measurements"], (
            f"{name} measurements mismatch"
        )
        assert stats1[name]["lab_reports"] == stats2[name]["lab_reports"], (
            f"{name} lab_reports mismatch"
        )


@pytest.mark.asyncio
async def test_priya_adherence_in_range(db: AsyncSession) -> None:
    """Priya's Levothyroxine 'taken' rate should be 80–99% (seeded at 95%)."""
    await seed_all(only="priya")

    uid = await _user_id(db, "demo-seed-priya")
    assert uid is not None

    levo = await db.execute(
        select(TrackedItem).where(
            TrackedItem.user_id == uid,
            TrackedItem.name == "Levothyroxine 75mcg",
        )
    )
    levo_item = levo.scalar_one()

    total = await _count_logs(db, uid)
    taken = await db.execute(
        select(func.count()).select_from(LogEntry).where(
            LogEntry.user_id == uid,
            LogEntry.tracked_item_id == levo_item.id,
            LogEntry.action == "taken",
        )
    )
    taken_count = taken.scalar_one()

    levo_total = await db.execute(
        select(func.count()).select_from(LogEntry).where(
            LogEntry.user_id == uid,
            LogEntry.tracked_item_id == levo_item.id,
        )
    )
    levo_total_count = levo_total.scalar_one()

    assert levo_total_count > 0, "No Levothyroxine log entries found"
    rate = taken_count / levo_total_count
    assert 0.80 <= rate <= 0.99, (
        f"Levo adherence {rate:.2%} outside expected 80–99% range"
    )

    # Also assert Priya has weight trending downward (start > end)
    weights = await db.execute(
        select(Measurement).where(
            Measurement.user_id == uid,
            Measurement.type == "weight",
        ).order_by(Measurement.measured_at)
    )
    weight_rows = weights.scalars().all()
    assert len(weight_rows) >= 5, "Expected at least 5 weight measurements for Priya"
    assert weight_rows[0].value > weight_rows[-1].value, (
        "Priya's weight should trend downward over 180 days"
    )


@pytest.mark.asyncio
async def test_rajesh_stress_week_visible(db: AsyncSession) -> None:
    """Rajesh's stress week (days -120 to -113) should show elevated BP systolic > 150."""
    await seed_all(only="rajesh")

    uid = await _user_id(db, "demo-seed-rajesh")
    assert uid is not None

    from scripts.seed.common import days_ago

    stress_start = days_ago(120)
    stress_end = days_ago(113)

    stress_bp = await db.execute(
        select(Measurement).where(
            Measurement.user_id == uid,
            Measurement.type == "bp_systolic",
            Measurement.measured_at >= stress_start,
            Measurement.measured_at <= stress_end,
        )
    )
    stress_readings = stress_bp.scalars().all()

    assert len(stress_readings) >= 3, (
        f"Expected at least 3 stress-week BP readings, got {len(stress_readings)}"
    )

    avg_systolic = sum(float(r.value) for r in stress_readings) / len(stress_readings)
    assert avg_systolic > 150, (
        f"Expected stress-week avg systolic > 150 mmHg, got {avg_systolic:.1f}"
    )
