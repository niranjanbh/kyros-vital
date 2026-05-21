"""Tests for /v1/wellness/reminders — update, soft delete."""

from datetime import date

from httpx import AsyncClient

_DEVICE = "reminders-test-device001"

_MED_ITEM = {
    "category": "medication",
    "name": "Test Med",
    "metadata": {"drug_name": "Aspirin", "dosage": "100mg", "form": "tablet"},
    "start_date": date.today().isoformat(),
}

_RECURRING_SCHEDULE = {
    "type": "recurring",
    "times": ["08:00"],
    "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    "start_date": date.today().isoformat(),
    "end_date": None,
    "timezone": "Asia/Kolkata",
}


async def _setup(client: AsyncClient, device_id: str = _DEVICE) -> tuple[str, str]:
    """Returns (item_id, reminder_id)."""
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        json=_MED_ITEM,
    )
    item_id = r.json()["id"]
    r = await client.post(
        f"/v1/wellness/tracked-items/{item_id}/reminders",
        headers={"X-Device-Id": device_id},
        json={"schedule": _RECURRING_SCHEDULE, "message_template": "Take {drug_name}"},
    )
    return item_id, r.json()["id"]


# ── create ────────────────────────────────────────────────────────────────────


async def test_create_reminder_returns_201(client: AsyncClient) -> None:
    device_id = "rem-create-device00001"
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        json=_MED_ITEM,
    )
    item_id = r.json()["id"]

    r = await client.post(
        f"/v1/wellness/tracked-items/{item_id}/reminders",
        headers={"X-Device-Id": device_id},
        json={"schedule": _RECURRING_SCHEDULE, "message_template": "Take it"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["active"] is True
    assert body["schedule"]["type"] == "recurring"
    assert body["channels"] == ["in_app"]


# ── update ────────────────────────────────────────────────────────────────────


async def test_patch_reminder_message_template(client: AsyncClient) -> None:
    device_id = "rem-patch-device00001"
    _, reminder_id = await _setup(client, device_id)

    r = await client.patch(
        f"/v1/wellness/reminders/{reminder_id}",
        headers={"X-Device-Id": device_id},
        json={"message_template": "Updated body"},
    )
    assert r.status_code == 200
    assert r.json()["message_template"] == "Updated body"


async def test_patch_reminder_schedule(client: AsyncClient) -> None:
    device_id = "rem-sched-device00001"
    _, reminder_id = await _setup(client, device_id)

    new_schedule = {**_RECURRING_SCHEDULE, "times": ["09:00", "21:00"]}
    r = await client.patch(
        f"/v1/wellness/reminders/{reminder_id}",
        headers={"X-Device-Id": device_id},
        json={"schedule": new_schedule},
    )
    assert r.status_code == 200
    assert r.json()["schedule"]["times"] == ["09:00", "21:00"]


# ── soft delete ────────────────────────────────────────────────────────────────


async def test_delete_reminder_sets_active_false(client: AsyncClient) -> None:
    device_id = "rem-delete-device00001"
    item_id, reminder_id = await _setup(client, device_id)

    r = await client.delete(
        f"/v1/wellness/reminders/{reminder_id}",
        headers={"X-Device-Id": device_id},
    )
    assert r.status_code == 204

    # Reminder still readable via the item's reminders list
    r = await client.get(
        f"/v1/wellness/tracked-items/{item_id}/reminders",
        headers={"X-Device-Id": device_id},
    )
    reminder = next(rem for rem in r.json() if rem["id"] == reminder_id)
    assert reminder["active"] is False


# ── schedule validation ────────────────────────────────────────────────────────


async def test_invalid_timezone_in_schedule_returns_422(client: AsyncClient) -> None:
    device_id = "rem-tz-device0000001"
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        json=_MED_ITEM,
    )
    item_id = r.json()["id"]

    bad_schedule = {**_RECURRING_SCHEDULE, "timezone": "Not/ATimezone"}
    r = await client.post(
        f"/v1/wellness/tracked-items/{item_id}/reminders",
        headers={"X-Device-Id": device_id},
        json={"schedule": bad_schedule, "message_template": "Fail"},
    )
    assert r.status_code == 422


async def test_active_window_end_before_start_returns_422(client: AsyncClient) -> None:
    device_id = "rem-win-device0000001"
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        json=_MED_ITEM,
    )
    item_id = r.json()["id"]

    bad_schedule = {
        "type": "interval",
        "interval_minutes": 120,
        "active_window": {"start": "22:00", "end": "08:00"},  # end < start
        "days_of_week": ["mon"],
        "timezone": "Asia/Kolkata",
    }
    r = await client.post(
        f"/v1/wellness/tracked-items/{item_id}/reminders",
        headers={"X-Device-Id": device_id},
        json={"schedule": bad_schedule, "message_template": "Fail"},
    )
    assert r.status_code == 422
