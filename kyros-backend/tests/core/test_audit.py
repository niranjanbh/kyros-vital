"""Tests for AuditMiddleware: mutating requests write audit_log rows."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.shared.models.audit_log import AuditLog

TEST_DATABASE_URL = "postgresql+asyncpg://kyros:kyros@localhost:5433/kyros_test"


async def _count_audit_rows(action_prefix: str) -> int:
    """Count audit_log rows matching action_prefix using a fresh session."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(bind=eng, expire_on_commit=False)
    async with factory() as s:
        result = await s.execute(
            select(func.count()).where(AuditLog.action.like(f"%{action_prefix}%"))
        )
        count: int = result.scalar_one()
    await eng.dispose()
    return count


async def test_patch_request_writes_audit_row(client, db: AsyncSession) -> None:
    device_id = "audit-test-device-0001"

    # Create the user
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    before = await _count_audit_rows("PATCH /v1/users/me")

    response = await client.patch(
        "/v1/users/me",
        headers={"X-Device-Id": device_id},
        json={"timezone": "Asia/Kolkata"},
    )
    assert response.status_code == 200

    after = await _count_audit_rows("PATCH /v1/users/me")
    assert after == before + 1


async def test_get_request_does_not_write_audit_row(client, db: AsyncSession) -> None:
    device_id = "audit-get-device-00001"
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    before = await _count_audit_rows("GET /v1/users/me")

    await client.get("/v1/users/me", headers={"X-Device-Id": device_id})

    after = await _count_audit_rows("GET /v1/users/me")
    # GET must NOT write an audit row
    assert after == before


async def test_audit_row_has_correct_fields(client, db: AsyncSession) -> None:
    device_id = "audit-fields-device001"
    r = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    user_id = r.json()["id"]

    # A PATCH on /me should produce an audit row with user_id and action filled
    await client.patch(
        "/v1/users/me",
        headers={"X-Device-Id": device_id},
        json={"timezone": "US/Pacific"},
    )

    # Use a fresh session to read the audit log (bypass identity-map cache)
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(bind=eng, expire_on_commit=False)
    async with factory() as s:
        result = await s.execute(
            select(AuditLog)
            .where(AuditLog.action.contains("PATCH /v1/users/me"))
            .order_by(AuditLog.occurred_at.desc())
            .limit(1)
        )
        row = result.scalar_one()

    await eng.dispose()

    assert str(row.user_id) == user_id
    assert row.actor_type == "user"
    assert "PATCH" in row.action
    assert row.resource_type == "me"
