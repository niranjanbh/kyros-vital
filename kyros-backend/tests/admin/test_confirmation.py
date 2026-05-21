"""Confirmation page pattern tests — wrong phrase rejects, right phrase commits."""
import os
import uuid
from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.audit_log import AuditLog
from app.shared.models.user import User
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem

os.environ.setdefault("ADMIN_USERNAME", "testadmin")


@pytest.fixture(autouse=True)
def _admin_creds(monkeypatch) -> None:
    import bcrypt
    hashed = bcrypt.hashpw(b"testpassword", bcrypt.gensalt()).decode()
    from app import config as cfg
    monkeypatch.setattr(cfg.settings, "ADMIN_USERNAME", "testadmin")
    monkeypatch.setattr(cfg.settings, "ADMIN_PASSWORD_HASH", hashed)


@pytest.fixture
async def active_item(db: AsyncSession) -> TrackedItem:
    user = User(id=uuid.uuid4(), device_id=f"conf-{uuid.uuid4().hex[:8]}")
    db.add(user)
    await db.flush()
    item = TrackedItem(
        id=uuid.uuid4(),
        user_id=user.id,
        category="medication",
        name="Test Medication",
        item_metadata={"drug_name": "Testinol", "dosage": "100mg", "form": "tablet"},
        status="active",
        start_date=date.today(),
    )
    db.add(item)
    await db.flush()
    return item


@pytest.mark.asyncio
async def test_confirmation_get_renders_form(
    client: AsyncClient, active_item: TrackedItem
) -> None:
    resp = await client.get(
        f"/admin/items/{active_item.id}/discontinue",
        auth=("testadmin", "testpassword"),
    )
    assert resp.status_code == 200
    assert b"DISCONTINUE" in resp.content
    assert b"confirmation" in resp.content


@pytest.mark.asyncio
async def test_wrong_phrase_does_not_mutate(
    client: AsyncClient, db: AsyncSession, active_item: TrackedItem
) -> None:
    resp = await client.post(
        f"/admin/items/{active_item.id}/discontinue",
        data={"confirmation": "WRONG"},
        auth=("testadmin", "testpassword"),
    )
    # Should redirect back with an error, not execute the action
    assert resp.status_code in (303, 200)

    # Item must still be active
    row = await db.execute(select(TrackedItem).where(TrackedItem.id == active_item.id))
    item = row.scalar_one()
    assert item.status == "active"


@pytest.mark.asyncio
async def test_correct_phrase_discontinues_and_audits(
    client: AsyncClient, db: AsyncSession, active_item: TrackedItem
) -> None:
    resp = await client.post(
        f"/admin/items/{active_item.id}/discontinue",
        data={"confirmation": "DISCONTINUE"},
        auth=("testadmin", "testpassword"),
        follow_redirects=False,
    )
    assert resp.status_code == 303

    # Refresh session
    await db.rollback()

    row = await db.execute(select(TrackedItem).where(TrackedItem.id == active_item.id))
    item = row.scalar_one()
    assert item.status == "discontinued"

    # Audit log entry must exist
    audit_row = await db.execute(
        select(AuditLog).where(AuditLog.action == "admin.write.discontinue_item")
    )
    entries = audit_row.scalars().all()
    assert len(entries) >= 1


@pytest.mark.asyncio
async def test_confirmation_wrong_phrase_shows_error(
    client: AsyncClient, active_item: TrackedItem
) -> None:
    """Wrong phrase should redirect back to confirmation page with ?error."""
    resp = await client.post(
        f"/admin/items/{active_item.id}/discontinue",
        data={"confirmation": "nope"},
        auth=("testadmin", "testpassword"),
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Wrong confirmation phrase" in resp.content or b"error" in resp.content.lower()
