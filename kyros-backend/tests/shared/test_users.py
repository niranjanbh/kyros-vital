"""Tests for POST /v1/users/guest, GET /v1/users/me, PATCH /v1/users/me."""

from httpx import AsyncClient

# ── POST /guest ───────────────────────────────────────────────────────────────


async def test_guest_new_device_returns_201(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/users/guest", headers={"X-Device-Id": "new-guest-device-p3001"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["device_id"] == "new-guest-device-p3001"
    assert body["subscription_tier"] == "free"
    assert "id" in body


async def test_guest_same_device_returns_same_user(client: AsyncClient) -> None:
    device_id = "idempotent-device-p30001"
    r1 = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    r2 = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    assert r1.status_code in (200, 201)
    assert r2.status_code in (200, 201)
    assert r1.json()["id"] == r2.json()["id"]


async def test_guest_second_call_returns_200(client: AsyncClient) -> None:
    device_id = "second-call-device-p3001"
    r1 = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    assert r1.status_code == 201

    r2 = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    assert r2.status_code == 200


async def test_guest_missing_device_id_returns_401(client: AsyncClient) -> None:
    response = await client.post("/v1/users/guest")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


async def test_guest_invalid_device_id_returns_401(client: AsyncClient) -> None:
    response = await client.post("/v1/users/guest", headers={"X-Device-Id": "too-short"})
    assert response.status_code == 401


# ── GET /me ───────────────────────────────────────────────────────────────────


async def test_get_me_with_valid_device_id(client: AsyncClient) -> None:
    device_id = "get-me-device-p300001"
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    response = await client.get("/v1/users/me", headers={"X-Device-Id": device_id})
    assert response.status_code == 200
    assert response.json()["device_id"] == device_id


async def test_get_me_without_device_id_returns_401(client: AsyncClient) -> None:
    response = await client.get("/v1/users/me")
    assert response.status_code == 401


async def test_get_me_creates_user_if_not_exists(client: AsyncClient) -> None:
    """GET /me also triggers find-or-create."""
    device_id = "get-me-creates-p30001"
    response = await client.get("/v1/users/me", headers={"X-Device-Id": device_id})
    assert response.status_code == 200
    assert response.json()["device_id"] == device_id


# ── PATCH /me ─────────────────────────────────────────────────────────────────


async def test_patch_me_updates_email_and_timezone(client: AsyncClient) -> None:
    device_id = "patch-me-device-p30001"
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    response = await client.patch(
        "/v1/users/me",
        headers={"X-Device-Id": device_id},
        json={"email": "user@example.com", "timezone": "US/Pacific"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["timezone"] == "US/Pacific"


async def test_patch_me_subscription_tier_rejected(client: AsyncClient) -> None:
    device_id = "patch-tier-device-p3001"
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})

    response = await client.patch(
        "/v1/users/me",
        headers={"X-Device-Id": device_id},
        json={"subscription_tier": "plus"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_patch_me_partial_update_preserves_other_fields(client: AsyncClient) -> None:
    device_id = "patch-partial-device001"
    r = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    original_tz = r.json()["timezone"]

    # Update only email
    r2 = await client.patch(
        "/v1/users/me",
        headers={"X-Device-Id": device_id},
        json={"email": "partial@example.com"},
    )
    assert r2.status_code == 200
    assert r2.json()["timezone"] == original_tz  # unchanged
    assert r2.json()["email"] == "partial@example.com"
