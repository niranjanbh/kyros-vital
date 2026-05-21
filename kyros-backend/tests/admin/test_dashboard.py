"""Dashboard metrics functions and page render tests."""
import os
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.services import metrics as svc
from app.clinic.models.consultation import Consultation
from app.shared.models.user import User
from app.wellness.models.log_entry import LogEntry
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem

# Ensure admin creds are configured
os.environ.setdefault("ADMIN_USERNAME", "testadmin")
os.environ.setdefault("ADMIN_PASSWORD_HASH", os.environ.get("ADMIN_PASSWORD_HASH", ""))

_AUTH = ("testadmin", os.environ.get("ADMIN_PASSWORD_HASH_PLAIN", "testpassword"))


@pytest.fixture(autouse=True)
def _setup_admin_env(monkeypatch) -> None:
    import bcrypt
    hashed = bcrypt.hashpw(b"testpassword", bcrypt.gensalt()).decode()
    from app import config as cfg
    monkeypatch.setattr(cfg.settings, "ADMIN_USERNAME", "testadmin")
    monkeypatch.setattr(cfg.settings, "ADMIN_PASSWORD_HASH", hashed)
    # Bust the in-process cache between tests
    svc._cache.clear()


@pytest.mark.asyncio
async def test_count_total_users(db: AsyncSession) -> None:
    u = User(id=uuid.uuid4(), device_id=f"dev-{uuid.uuid4().hex[:8]}")
    db.add(u)
    await db.flush()
    total = await svc.count_total_users(db)
    assert total >= 1


@pytest.mark.asyncio
async def test_items_by_status_shape(db: AsyncSession) -> None:
    result = await svc.items_by_status(db)
    assert isinstance(result, dict)
    for v in result.values():
        assert isinstance(v, int)


@pytest.mark.asyncio
async def test_consultations_by_status_shape(db: AsyncSession) -> None:
    result = await svc.consultations_by_status(db)
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_revenue_last_30_days_is_integer(db: AsyncSession) -> None:
    result = await svc.revenue_last_30_days(db)
    assert isinstance(result, int)


@pytest.mark.asyncio
async def test_dashboard_renders_200(client: AsyncClient) -> None:
    resp = await client.get("/admin/", auth=("testadmin", "testpassword"))
    assert resp.status_code == 200
    # All metric blocks should be present
    assert b"Users" in resp.content
    assert b"Items" in resp.content
    assert b"Reminders" in resp.content
    assert b"Consultations" in resp.content
    assert b"System" in resp.content


@pytest.mark.asyncio
async def test_dashboard_cache(db: AsyncSession) -> None:
    """Calling get_dashboard_metrics twice returns the cached value the second time."""
    svc._cache.clear()
    result1 = await svc.get_dashboard_metrics(db)
    result2 = await svc.get_dashboard_metrics(db)
    assert result1 is result2  # same object = cache hit
