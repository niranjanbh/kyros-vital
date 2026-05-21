"""Tests for get_current_user guest-auth dependency."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.user import User


async def test_missing_device_id_returns_401(client: AsyncClient) -> None:
    response = await client.get("/v1/users/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"


async def test_invalid_device_id_returns_401(client: AsyncClient) -> None:
    # Too short (< 16 chars)
    response = await client.get("/v1/users/me", headers={"X-Device-Id": "short"})
    assert response.status_code == 401


async def test_new_device_id_creates_user(client: AsyncClient, db: AsyncSession) -> None:
    device_id = "new-device-auth-test01"
    response = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    assert response.status_code == 201  # 201 for first creation
    body = response.json()
    assert body["device_id"] == device_id
    assert body["subscription_tier"] == "free"

    # Verify row exists in DB
    result = await db.execute(select(User).where(User.device_id == device_id))
    user = result.scalar_one_or_none()
    assert user is not None
    assert str(user.id) == body["id"]


async def test_same_device_id_returns_same_user(client: AsyncClient) -> None:
    device_id = "stable-device-auth-0001"

    r1 = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    r2 = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    assert r1.status_code == 201  # first creation
    assert r2.status_code == 200  # idempotent repeat
    # Same user UUID returned both times
    assert r1.json()["id"] == r2.json()["id"]


async def test_get_me_returns_user(client: AsyncClient) -> None:
    device_id = "get-me-device-test001"
    # Create user first
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    response = await client.get("/v1/users/me", headers={"X-Device-Id": device_id})
    assert response.status_code == 200
    assert response.json()["device_id"] == device_id


async def test_patch_me_updates_timezone(client: AsyncClient) -> None:
    device_id = "patch-me-device-test01"
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    response = await client.patch(
        "/v1/users/me",
        headers={"X-Device-Id": device_id},
        json={"timezone": "US/Eastern"},
    )
    assert response.status_code == 200
    assert response.json()["timezone"] == "US/Eastern"
