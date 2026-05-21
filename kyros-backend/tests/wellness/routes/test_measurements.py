"""Tests for /v1/wellness/measurements."""

from httpx import AsyncClient

_DEVICE = "measurements-dev-00001"

_WEIGHT_PAYLOAD = {
    "type": "weight",
    "value": "72.4",
    "unit": "kg",
    "measured_at": "2026-05-20T08:00:00Z",
}


async def _ensure_user(client: AsyncClient, device_id: str = _DEVICE) -> None:
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})


# ── CRUD lifecycle ─────────────────────────────────────────────────────────────


async def test_create_measurement_returns_201(client: AsyncClient) -> None:
    await _ensure_user(client)
    r = await client.post(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": _DEVICE},
        json=_WEIGHT_PAYLOAD,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["type"] == "weight"
    assert float(body["value"]) == pytest_approx(72.4)
    assert body["unit"] == "kg"


async def test_get_measurement(client: AsyncClient) -> None:
    await _ensure_user(client)
    r = await client.post(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": _DEVICE},
        json=_WEIGHT_PAYLOAD,
    )
    mid = r.json()["id"]

    r = await client.get(f"/v1/wellness/measurements/{mid}", headers={"X-Device-Id": _DEVICE})
    assert r.status_code == 200
    assert r.json()["id"] == mid


async def test_patch_measurement(client: AsyncClient) -> None:
    device_id = "meas-patch-device-0001"
    await _ensure_user(client, device_id)
    r = await client.post(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": device_id},
        json=_WEIGHT_PAYLOAD,
    )
    mid = r.json()["id"]

    r = await client.patch(
        f"/v1/wellness/measurements/{mid}",
        headers={"X-Device-Id": device_id},
        json={"value": "73.1", "note": "After breakfast"},
    )
    assert r.status_code == 200
    assert float(r.json()["value"]) == pytest_approx(73.1)
    assert r.json()["note"] == "After breakfast"


async def test_delete_measurement_hard_deletes(client: AsyncClient) -> None:
    device_id = "meas-delete-device001"
    await _ensure_user(client, device_id)
    r = await client.post(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": device_id},
        json=_WEIGHT_PAYLOAD,
    )
    mid = r.json()["id"]

    r = await client.delete(
        f"/v1/wellness/measurements/{mid}", headers={"X-Device-Id": device_id}
    )
    assert r.status_code == 204

    # Hard delete: row is gone → 404
    r = await client.get(
        f"/v1/wellness/measurements/{mid}", headers={"X-Device-Id": device_id}
    )
    assert r.status_code == 404


async def test_full_crud_lifecycle(client: AsyncClient) -> None:
    device_id = "meas-lifecycle-dev001"
    await _ensure_user(client, device_id)

    r = await client.post(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": device_id},
        json={"type": "heart_rate", "value": "72", "unit": "bpm", "measured_at": "2026-05-20T09:00:00Z"},
    )
    assert r.status_code == 201
    mid = r.json()["id"]

    r = await client.get(f"/v1/wellness/measurements/{mid}", headers={"X-Device-Id": device_id})
    assert r.status_code == 200

    r = await client.patch(
        f"/v1/wellness/measurements/{mid}",
        headers={"X-Device-Id": device_id},
        json={"value": "75"},
    )
    assert r.status_code == 200
    assert float(r.json()["value"]) == pytest_approx(75.0)

    r = await client.delete(f"/v1/wellness/measurements/{mid}", headers={"X-Device-Id": device_id})
    assert r.status_code == 204

    r = await client.get(f"/v1/wellness/measurements/{mid}", headers={"X-Device-Id": device_id})
    assert r.status_code == 404


# ── filtering ─────────────────────────────────────────────────────────────────


async def test_filter_by_type(client: AsyncClient) -> None:
    device_id = "meas-type-filter-0001"
    await _ensure_user(client, device_id)

    await client.post(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": device_id},
        json={"type": "weight", "value": "72", "unit": "kg", "measured_at": "2026-05-20T08:00:00Z"},
    )
    await client.post(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": device_id},
        json={"type": "heart_rate", "value": "72", "unit": "bpm", "measured_at": "2026-05-20T08:00:00Z"},
    )

    r = await client.get(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": device_id},
        params={"type": "weight"},
    )
    assert r.status_code == 200
    assert all(m["type"] == "weight" for m in r.json())


async def test_filter_by_time_range(client: AsyncClient) -> None:
    device_id = "meas-time-filter-0001"
    await _ensure_user(client, device_id)

    for ts in ["2026-05-18T08:00:00Z", "2026-05-19T08:00:00Z", "2026-05-21T08:00:00Z"]:
        await client.post(
            "/v1/wellness/measurements/",
            headers={"X-Device-Id": device_id},
            json={"type": "weight", "value": "72", "unit": "kg", "measured_at": ts},
        )

    r = await client.get(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": device_id},
        params={"from": "2026-05-19T00:00:00Z", "to": "2026-05-20T00:00:00Z"},
    )
    assert r.status_code == 200
    measurements = r.json()
    assert len(measurements) == 1
    assert "2026-05-19" in measurements[0]["measured_at"]


# ── cross-user isolation ──────────────────────────────────────────────────────


async def test_cross_user_get_returns_404(client: AsyncClient) -> None:
    device_a = "meas-cross-a-device001"
    device_b = "meas-cross-b-device001"
    await _ensure_user(client, device_a)
    await _ensure_user(client, device_b)

    r = await client.post(
        "/v1/wellness/measurements/",
        headers={"X-Device-Id": device_a},
        json=_WEIGHT_PAYLOAD,
    )
    mid = r.json()["id"]

    r = await client.get(f"/v1/wellness/measurements/{mid}", headers={"X-Device-Id": device_b})
    assert r.status_code == 404


# ── pytest.approx import ──────────────────────────────────────────────────────

from pytest import approx as pytest_approx  # noqa: E402
