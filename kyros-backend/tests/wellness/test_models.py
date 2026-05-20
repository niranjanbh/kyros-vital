"""Model-layer tests: save/fetch, cascade deletes, FK SET NULL, unique fire_key."""

from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.audit_log import AuditLog
from app.shared.models.user import User
from app.wellness.models.lab_report import LabReport
from app.wellness.models.log_entry import LogEntry
from app.wellness.models.measurement import Measurement
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem

# ── helpers ──────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(tz=UTC)


async def _make_user(db: AsyncSession, device_id: str = "test-device-00000001") -> User:
    user = User(device_id=device_id, timezone="Asia/Kolkata")
    db.add(user)
    await db.flush()
    return user


async def _make_item(
    db: AsyncSession, user_id: object, category: str = "medication"
) -> TrackedItem:
    item = TrackedItem(
        user_id=user_id,
        category=category,
        name="Test Item",
        item_metadata={"drug_name": "Aspirin", "dosage": "100mg", "form": "tablet"},
        start_date=date.today(),
    )
    db.add(item)
    await db.flush()
    return item


async def _make_reminder(db: AsyncSession, tracked_item_id: object) -> Reminder:
    reminder = Reminder(
        tracked_item_id=tracked_item_id,
        schedule={
            "type": "recurring",
            "times": ["08:00"],
            "days_of_week": ["mon"],
            "start_date": date.today().isoformat(),
            "end_date": None,
            "timezone": "Asia/Kolkata",
        },
        message_template="Take your meds",
        channels=["in_app"],
    )
    db.add(reminder)
    await db.flush()
    return reminder


async def _make_log_entry(
    db: AsyncSession,
    user_id: object,
    tracked_item_id: object,
    reminder_id: object | None = None,
    fire_key: str | None = None,
) -> LogEntry:
    entry = LogEntry(
        user_id=user_id,
        tracked_item_id=tracked_item_id,
        reminder_id=reminder_id,
        fire_key=fire_key,
        action="taken",
        occurred_at=_now(),
    )
    db.add(entry)
    await db.flush()
    return entry


# ── save / fetch ──────────────────────────────────────────────────────────────


async def test_save_fetch_user(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-savefetch1")
    result = await db.execute(select(User).where(User.id == user.id))
    fetched = result.scalar_one()
    assert fetched.device_id == "test-device-savefetch1"
    assert fetched.subscription_tier == "free"
    assert fetched.timezone == "Asia/Kolkata"


async def test_save_fetch_tracked_item(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-item00001")
    item = await _make_item(db, user.id, "medication")
    result = await db.execute(select(TrackedItem).where(TrackedItem.id == item.id))
    fetched = result.scalar_one()
    assert fetched.category == "medication"
    assert fetched.status == "active"
    assert fetched.item_metadata["drug_name"] == "Aspirin"


async def test_save_fetch_reminder(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-rem000001")
    item = await _make_item(db, user.id)
    reminder = await _make_reminder(db, item.id)
    result = await db.execute(select(Reminder).where(Reminder.id == reminder.id))
    fetched = result.scalar_one()
    assert fetched.active is True
    assert fetched.channels == ["in_app"]
    assert fetched.schedule["type"] == "recurring"


async def test_save_fetch_log_entry(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-log000001")
    item = await _make_item(db, user.id)
    entry = await _make_log_entry(db, user.id, item.id, fire_key="test-fk-001")
    result = await db.execute(select(LogEntry).where(LogEntry.id == entry.id))
    fetched = result.scalar_one()
    assert fetched.action == "taken"
    assert fetched.fire_key == "test-fk-001"


async def test_save_fetch_measurement(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-meas00001")
    m = Measurement(
        user_id=user.id,
        type="weight",
        value="72.5",
        unit="kg",
        measured_at=_now(),
    )
    db.add(m)
    await db.flush()
    result = await db.execute(select(Measurement).where(Measurement.id == m.id))
    fetched = result.scalar_one()
    assert fetched.type == "weight"
    assert float(fetched.value) == pytest.approx(72.5)


async def test_save_fetch_lab_report(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-lab000001")
    report = LabReport(
        user_id=user.id,
        report_date=date.today(),
        lab_name="City Lab",
        parsed={"tests": []},
    )
    db.add(report)
    await db.flush()
    result = await db.execute(select(LabReport).where(LabReport.id == report.id))
    fetched = result.scalar_one()
    assert fetched.lab_name == "City Lab"
    assert fetched.status == "active"


async def test_save_fetch_audit_log(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-audit0001")
    entry = AuditLog(
        user_id=user.id,
        actor_type="user",
        action="POST /v1/wellness/tracked-items",
        resource_type="tracked-items",
    )
    db.add(entry)
    await db.flush()
    result = await db.execute(select(AuditLog).where(AuditLog.id == entry.id))
    fetched = result.scalar_one()
    assert fetched.actor_type == "user"
    assert fetched.user_id == user.id


# ── cascade deletes ───────────────────────────────────────────────────────────


async def test_cascade_delete_user_removes_items_reminders_logs(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-casc00001")
    item = await _make_item(db, user.id)
    reminder = await _make_reminder(db, item.id)
    log = await _make_log_entry(db, user.id, item.id, reminder_id=reminder.id)
    await db.commit()

    user_id = user.id
    item_id = item.id
    reminder_id = reminder.id
    log_id = log.id

    # Delete the user — DB cascades to items → reminders → log entries
    await db.delete(user)
    await db.commit()
    # expire_all() clears the identity map so db.get() hits the DB, not cache
    db.expire_all()

    assert (await db.get(User, user_id)) is None
    assert (await db.get(TrackedItem, item_id)) is None
    assert (await db.get(Reminder, reminder_id)) is None
    assert (await db.get(LogEntry, log_id)) is None


async def test_cascade_delete_item_removes_reminders_and_logs(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-casc00002")
    item = await _make_item(db, user.id)
    reminder = await _make_reminder(db, item.id)
    log = await _make_log_entry(db, user.id, item.id, reminder_id=reminder.id)
    await db.commit()

    item_id = item.id
    reminder_id = reminder.id
    log_id = log.id

    await db.delete(item)
    await db.commit()
    db.expire_all()

    assert (await db.get(TrackedItem, item_id)) is None
    assert (await db.get(Reminder, reminder_id)) is None
    assert (await db.get(LogEntry, log_id)) is None


# ── reminder deletion sets log_entry.reminder_id to NULL (SET NULL) ───────────


async def test_delete_reminder_nullifies_log_entry_reminder_id(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-setnull01")
    item = await _make_item(db, user.id)
    reminder = await _make_reminder(db, item.id)
    log = await _make_log_entry(db, user.id, item.id, reminder_id=reminder.id)
    await db.commit()

    log_id = log.id

    await db.delete(reminder)
    await db.commit()

    # Expire the cached log entry so we get a fresh fetch
    db.expire_all()
    fetched_log = await db.get(LogEntry, log_id)
    assert fetched_log is not None
    assert fetched_log.reminder_id is None


# ── unique fire_key partial index ─────────────────────────────────────────────


async def test_duplicate_fire_key_raises_integrity_error(db: AsyncSession) -> None:
    user = await _make_user(db, "test-device-firekey1")
    item = await _make_item(db, user.id)
    await db.commit()

    fire_key = f"unique-fire-key-{user.id}"

    # First insert — must succeed
    log1 = LogEntry(
        user_id=user.id,
        tracked_item_id=item.id,
        fire_key=fire_key,
        action="taken",
        occurred_at=_now(),
    )
    db.add(log1)
    await db.commit()

    # Second insert with same fire_key — must raise IntegrityError
    log2 = LogEntry(
        user_id=user.id,
        tracked_item_id=item.id,
        fire_key=fire_key,
        action="taken",
        occurred_at=_now(),
    )
    db.add(log2)
    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


async def test_null_fire_key_not_subject_to_unique_constraint(db: AsyncSession) -> None:
    """NULL fire_key is excluded from the partial unique index — many NULLs are fine."""
    user = await _make_user(db, "test-device-firekey2")
    item = await _make_item(db, user.id)
    await db.commit()

    for _ in range(3):
        entry = LogEntry(
            user_id=user.id,
            tracked_item_id=item.id,
            fire_key=None,
            action="acknowledged",
            occurred_at=_now(),
        )
        db.add(entry)

    # Should not raise — NULLs are not constrained
    await db.flush()
    await db.rollback()
