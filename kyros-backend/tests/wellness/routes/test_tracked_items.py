"""Tests for /v1/wellness/tracked-items CRUD + sub-resource reminders."""

from datetime import date

from httpx import AsyncClient

# ── helpers ───────────────────────────────────────────────────────────────────

_DEVICE_A = "tracked-items-device-a001"
_DEVICE_B = "tracked-items-device-b001"

_MED_PAYLOAD = {
    "category": "medication",
    "name": "Metformin 500mg",
    "metadata": {
        "drug_name": "Metformin",
        "dosage": "500mg",
        "form": "tablet",
        "with_food": True,
    },
    "start_date": date.today().isoformat(),
}

_RECURRING_SCHEDULE = {
    "type": "recurring",
    "times": ["08:00", "20:00"],
    "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    "start_date": date.today().isoformat(),
    "end_date": None,
    "timezone": "Asia/Kolkata",
}


async def _ensure_user(client: AsyncClient, device_id: str) -> dict:
    r = await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})
    assert r.status_code in (200, 201)
    return r.json()


async def _create_item(client: AsyncClient, device_id: str, payload: dict = _MED_PAYLOAD) -> dict:
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        json=payload,
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── CRUD lifecycle ─────────────────────────────────────────────────────────────


async def test_create_medication_returns_201(client: AsyncClient) -> None:
    await _ensure_user(client, _DEVICE_A)
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": _DEVICE_A},
        json=_MED_PAYLOAD,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["category"] == "medication"
    assert body["name"] == "Metformin 500mg"
    assert body["status"] == "active"
    assert body["metadata"]["drug_name"] == "Metformin"
    assert isinstance(body["reminders"], list)


async def test_list_tracked_items(client: AsyncClient) -> None:
    await _ensure_user(client, _DEVICE_A)
    await _create_item(client, _DEVICE_A)
    r = await client.get(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": _DEVICE_A},
    )
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_list_filter_by_category(client: AsyncClient) -> None:
    device_id = "filter-cat-device-p4001"
    await _ensure_user(client, device_id)
    await _create_item(client, device_id)
    # Filter for water — should not include the medication
    r = await client.get(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        params={"category": "water"},
    )
    assert r.status_code == 200
    assert all(i["category"] == "water" for i in r.json())


async def test_get_tracked_item(client: AsyncClient) -> None:
    await _ensure_user(client, _DEVICE_A)
    item = await _create_item(client, _DEVICE_A)
    r = await client.get(
        f"/v1/wellness/tracked-items/{item['id']}",
        headers={"X-Device-Id": _DEVICE_A},
    )
    assert r.status_code == 200
    assert r.json()["id"] == item["id"]


async def test_patch_tracked_item(client: AsyncClient) -> None:
    device_id = "patch-item-device-p4001"
    await _ensure_user(client, device_id)
    item = await _create_item(client, device_id)
    r = await client.patch(
        f"/v1/wellness/tracked-items/{item['id']}",
        headers={"X-Device-Id": device_id},
        json={"name": "Metformin 1000mg"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Metformin 1000mg"


async def test_full_crud_lifecycle_medication(client: AsyncClient) -> None:
    device_id = "lifecycle-device-p40001"
    await _ensure_user(client, device_id)

    # Create
    item = await _create_item(client, device_id)
    item_id = item["id"]

    # Read
    r = await client.get(
        f"/v1/wellness/tracked-items/{item_id}",
        headers={"X-Device-Id": device_id},
    )
    assert r.status_code == 200

    # Update
    r = await client.patch(
        f"/v1/wellness/tracked-items/{item_id}",
        headers={"X-Device-Id": device_id},
        json={"name": "Updated Name"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"

    # Delete (soft)
    r = await client.delete(
        f"/v1/wellness/tracked-items/{item_id}",
        headers={"X-Device-Id": device_id},
    )
    assert r.status_code == 204

    # Still readable after soft delete
    r = await client.get(
        f"/v1/wellness/tracked-items/{item_id}",
        headers={"X-Device-Id": device_id},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "discontinued"


# ── soft delete cascade ────────────────────────────────────────────────────────


async def test_soft_delete_deactivates_child_reminders(client: AsyncClient) -> None:
    device_id = "softdel-device-p400001"
    await _ensure_user(client, device_id)
    item = await _create_item(client, device_id)
    item_id = item["id"]

    # Create a reminder
    r = await client.post(
        f"/v1/wellness/tracked-items/{item_id}/reminders",
        headers={"X-Device-Id": device_id},
        json={"schedule": _RECURRING_SCHEDULE, "message_template": "Take {drug_name}"},
    )
    assert r.status_code == 201
    reminder_id = r.json()["id"]

    # Soft-delete the item
    await client.delete(
        f"/v1/wellness/tracked-items/{item_id}",
        headers={"X-Device-Id": device_id},
    )

    # Item is discontinued
    r = await client.get(
        f"/v1/wellness/tracked-items/{item_id}",
        headers={"X-Device-Id": device_id},
    )
    assert r.json()["status"] == "discontinued"

    # Reminder is deactivated
    reminder = next(rem for rem in r.json()["reminders"] if rem["id"] == reminder_id)
    assert reminder["active"] is False


# ── cross-user isolation ───────────────────────────────────────────────────────


async def test_cross_user_get_returns_404(client: AsyncClient) -> None:
    await _ensure_user(client, _DEVICE_A)
    await _ensure_user(client, _DEVICE_B)
    item = await _create_item(client, _DEVICE_A)

    # User B tries to read user A's item
    r = await client.get(
        f"/v1/wellness/tracked-items/{item['id']}",
        headers={"X-Device-Id": _DEVICE_B},
    )
    assert r.status_code == 404


async def test_cross_user_patch_returns_404(client: AsyncClient) -> None:
    await _ensure_user(client, _DEVICE_A)
    await _ensure_user(client, _DEVICE_B)
    item = await _create_item(client, _DEVICE_A)

    r = await client.patch(
        f"/v1/wellness/tracked-items/{item['id']}",
        headers={"X-Device-Id": _DEVICE_B},
        json={"name": "Hijack"},
    )
    assert r.status_code == 404


# ── metadata validation ────────────────────────────────────────────────────────


async def test_invalid_metadata_wrong_category_shape_returns_422(client: AsyncClient) -> None:
    await _ensure_user(client, _DEVICE_A)
    # Send water metadata for a medication category
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": _DEVICE_A},
        json={
            "category": "medication",
            "name": "Bad Item",
            "metadata": {"daily_target_ml": 2000},  # water meta, not medication
            "start_date": date.today().isoformat(),
        },
    )
    assert r.status_code == 422
    # FastAPI returns field-level validation errors
    detail = r.json()
    assert "detail" in detail or "error" in detail


async def test_invalid_metadata_missing_required_field_returns_422(client: AsyncClient) -> None:
    await _ensure_user(client, _DEVICE_A)
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": _DEVICE_A},
        json={
            "category": "medication",
            "name": "Bad Item",
            "metadata": {"drug_name": "Aspirin"},  # missing dosage and form
            "start_date": date.today().isoformat(),
        },
    )
    assert r.status_code == 422


# ── reminders sub-resource ─────────────────────────────────────────────────────


async def test_create_and_list_reminders(client: AsyncClient) -> None:
    device_id = "reminder-sub-device001"
    await _ensure_user(client, device_id)
    item = await _create_item(client, device_id)
    item_id = item["id"]

    # Create reminder
    r = await client.post(
        f"/v1/wellness/tracked-items/{item_id}/reminders",
        headers={"X-Device-Id": device_id},
        json={"schedule": _RECURRING_SCHEDULE, "message_template": "Take {drug_name}"},
    )
    assert r.status_code == 201
    assert r.json()["active"] is True

    # List reminders
    r = await client.get(
        f"/v1/wellness/tracked-items/{item_id}/reminders",
        headers={"X-Device-Id": device_id},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
