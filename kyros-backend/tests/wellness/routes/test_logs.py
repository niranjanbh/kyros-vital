"""Tests for /v1/wellness/logs."""

from datetime import date

from httpx import AsyncClient

# ── helpers ───────────────────────────────────────────────────────────────────


async def _setup(client: AsyncClient, device_id: str) -> tuple[str, str]:
    """Create user + medication item. Returns (device_id, item_id)."""
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        json={
            "category": "medication",
            "name": "Aspirin",
            "metadata": {"drug_name": "Aspirin", "dosage": "100mg", "form": "tablet"},
            "start_date": date.today().isoformat(),
        },
    )
    assert r.status_code == 201, r.text
    return device_id, r.json()["id"]


def _log_payload(item_id: str, fire_key: str | None = None) -> dict:
    return {
        "tracked_item_id": item_id,
        "action": "taken",
        "occurred_at": "2026-05-20T08:00:00+05:30",
        "fire_key": fire_key,
    }


# ── idempotency ───────────────────────────────────────────────────────────────


async def test_post_new_fire_key_returns_201(client: AsyncClient) -> None:
    device_id = "logs-new-fk-device-001"
    _, item_id = await _setup(client, device_id)

    r = await client.post(
        "/v1/wellness/logs/",
        headers={"X-Device-Id": device_id},
        json=_log_payload(item_id, fire_key=f"rem-abc:{device_id}:2026-05-20T08:00:00+05:30"),
    )
    assert r.status_code == 201
    body = r.json()
    assert body["action"] == "taken"
    assert body["fire_key"] is not None
    assert "id" in body


async def test_post_same_fire_key_returns_200_same_row(client: AsyncClient) -> None:
    device_id = "logs-dup-fk-device-0001"
    _, item_id = await _setup(client, device_id)
    fire_key = f"rem-xyz:{device_id}:2026-05-20T08:00:00+05:30"
    payload = _log_payload(item_id, fire_key=fire_key)

    r1 = await client.post(
        "/v1/wellness/logs/", headers={"X-Device-Id": device_id}, json=payload
    )
    r2 = await client.post(
        "/v1/wellness/logs/", headers={"X-Device-Id": device_id}, json=payload
    )

    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]


async def test_post_no_fire_key_always_inserts(client: AsyncClient) -> None:
    device_id = "logs-nofk-device-0001"
    _, item_id = await _setup(client, device_id)
    payload = _log_payload(item_id)  # no fire_key

    r1 = await client.post(
        "/v1/wellness/logs/", headers={"X-Device-Id": device_id}, json=payload
    )
    r2 = await client.post(
        "/v1/wellness/logs/", headers={"X-Device-Id": device_id}, json=payload
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] != r2.json()["id"]  # two distinct rows


async def test_race_condition_same_fire_key_no_duplicate(client: AsyncClient) -> None:
    """
    Race condition simulation: repeated POSTs with the same fire_key produce exactly
    one row. The ON CONFLICT DO NOTHING path handles DB-level races; this test
    exercises the application path (first → 201, subsequent → 200, same id).
    """
    device_id = "logs-race-device-00001"
    _, item_id = await _setup(client, device_id)
    fire_key = f"rem-race:{device_id}:2026-05-20T08:00:00+05:30"
    payload = _log_payload(item_id, fire_key=fire_key)

    r1 = await client.post(
        "/v1/wellness/logs/", headers={"X-Device-Id": device_id}, json=payload
    )
    r2 = await client.post(
        "/v1/wellness/logs/", headers={"X-Device-Id": device_id}, json=payload
    )
    r3 = await client.post(
        "/v1/wellness/logs/", headers={"X-Device-Id": device_id}, json=payload
    )

    assert r1.status_code == 201
    assert r2.status_code == 200
    assert r3.status_code == 200
    assert r1.json()["id"] == r2.json()["id"] == r3.json()["id"]


# ── filtering ─────────────────────────────────────────────────────────────────


async def test_filter_by_tracked_item_id(client: AsyncClient) -> None:
    device_id = "logs-filter-item-0001"
    _, item_a = await _setup(client, device_id)
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        json={
            "category": "water",
            "name": "Hydration",
            "metadata": {"daily_target_ml": 2000, "glass_size_ml": 250},
            "start_date": date.today().isoformat(),
        },
    )
    item_b = r.json()["id"]

    await client.post(
        "/v1/wellness/logs/",
        headers={"X-Device-Id": device_id},
        json={"tracked_item_id": item_a, "action": "taken", "occurred_at": "2026-05-20T08:00:00Z"},
    )
    await client.post(
        "/v1/wellness/logs/",
        headers={"X-Device-Id": device_id},
        json={"tracked_item_id": item_b, "action": "logged_value", "occurred_at": "2026-05-20T09:00:00Z"},
    )

    r = await client.get(
        "/v1/wellness/logs/",
        headers={"X-Device-Id": device_id},
        params={"tracked_item_id": item_a},
    )
    assert r.status_code == 200
    assert all(log["tracked_item_id"] == item_a for log in r.json())


async def test_filter_by_action(client: AsyncClient) -> None:
    device_id = "logs-filter-action001"
    _, item_id = await _setup(client, device_id)

    await client.post(
        "/v1/wellness/logs/",
        headers={"X-Device-Id": device_id},
        json={"tracked_item_id": item_id, "action": "taken", "occurred_at": "2026-05-20T08:00:00Z"},
    )
    await client.post(
        "/v1/wellness/logs/",
        headers={"X-Device-Id": device_id},
        json={"tracked_item_id": item_id, "action": "skipped", "occurred_at": "2026-05-20T20:00:00Z"},
    )

    r = await client.get(
        "/v1/wellness/logs/",
        headers={"X-Device-Id": device_id},
        params={"action": "taken"},
    )
    assert r.status_code == 200
    assert all(log["action"] == "taken" for log in r.json())


async def test_filter_by_date_range(client: AsyncClient) -> None:
    device_id = "logs-filter-date-0001"
    _, item_id = await _setup(client, device_id)

    for ts in ["2026-05-18T08:00:00Z", "2026-05-19T08:00:00Z", "2026-05-21T08:00:00Z"]:
        await client.post(
            "/v1/wellness/logs/",
            headers={"X-Device-Id": device_id},
            json={"tracked_item_id": item_id, "action": "taken", "occurred_at": ts},
        )

    r = await client.get(
        "/v1/wellness/logs/",
        headers={"X-Device-Id": device_id},
        params={"from": "2026-05-19T00:00:00Z", "to": "2026-05-20T00:00:00Z"},
    )
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) == 1
    assert "2026-05-19" in logs[0]["occurred_at"]


# ── cross-user isolation ──────────────────────────────────────────────────────


async def test_cross_user_logs_not_visible(client: AsyncClient) -> None:
    """User B cannot see User A's log entries."""
    device_a = "logs-cross-a-device001"
    device_b = "logs-cross-b-device001"
    _, item_id = await _setup(client, device_a)
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_b})

    await client.post(
        "/v1/wellness/logs/",
        headers={"X-Device-Id": device_a},
        json={"tracked_item_id": item_id, "action": "taken", "occurred_at": "2026-05-20T08:00:00Z"},
    )

    r = await client.get("/v1/wellness/logs/", headers={"X-Device-Id": device_b})
    assert r.status_code == 200
    assert r.json() == []
