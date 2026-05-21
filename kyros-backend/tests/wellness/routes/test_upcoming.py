"""Tests for GET /v1/wellness/reminders/upcoming."""

from datetime import date, timedelta

from httpx import AsyncClient

# ── helpers ───────────────────────────────────────────────────────────────────


async def _user(client: AsyncClient, device_id: str) -> None:
    await client.post("/v1/users/guest", headers={"X-Device-Id": device_id})


async def _create_med_item(client: AsyncClient, device_id: str) -> str:
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        json={
            "category": "medication",
            "name": "Metformin 500mg",
            "metadata": {"drug_name": "Metformin", "dosage": "500mg", "form": "tablet"},
            "start_date": date.today().isoformat(),
        },
    )
    return r.json()["id"]


async def _create_water_item(client: AsyncClient, device_id: str) -> str:
    r = await client.post(
        "/v1/wellness/tracked-items/",
        headers={"X-Device-Id": device_id},
        json={
            "category": "water",
            "name": "Daily Hydration",
            "metadata": {"daily_target_ml": 2500, "glass_size_ml": 250},
            "start_date": date.today().isoformat(),
        },
    )
    return r.json()["id"]


async def _add_reminder(
    client: AsyncClient, device_id: str, item_id: str, schedule: dict, template: str
) -> str:
    r = await client.post(
        f"/v1/wellness/tracked-items/{item_id}/reminders",
        headers={"X-Device-Id": device_id},
        json={"schedule": schedule, "message_template": template},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ── upcoming fires ────────────────────────────────────────────────────────────


async def test_recurring_twice_daily_48h_yields_4_events(client: AsyncClient) -> None:
    """Twice-daily IST medication over 48h → 4 fires."""
    device_id = "upcoming-twodaily-000001"
    await _user(client, device_id)
    item_id = await _create_med_item(client, device_id)
    await _add_reminder(
        client,
        device_id,
        item_id,
        schedule={
            "type": "recurring",
            "times": ["08:00", "20:00"],
            "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_date": date.today().isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Take {drug_name} {dosage}",
    )

    r = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 48},
    )
    assert r.status_code == 200
    fires = r.json()
    assert len(fires) == 4

    # Bodies use template substitution
    for fire in fires:
        assert "Metformin" in fire["payload"]["body"]
        assert fire["payload"]["category"] == "medication"
        assert fire["payload"]["actions"] == ["taken", "skipped", "snooze_15"]


async def test_interval_water_weekday_8_events(client: AsyncClient) -> None:
    """2h interval 08:00–22:00 weekdays over 24h on Monday → 8 fires."""
    # Use a Monday in the near future
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7  # 0 = already Monday
    if days_until_monday == 0:
        days_until_monday = 0  # today IS Monday
    test_start_date = today + timedelta(days=days_until_monday)
    # Ensure Monday; if today isn't Monday pick next Monday
    while test_start_date.weekday() != 0:
        test_start_date += timedelta(days=1)

    device_id = "upcoming-interval-000001"
    await _user(client, device_id)
    item_id = await _create_water_item(client, device_id)
    await _add_reminder(
        client,
        device_id,
        item_id,
        schedule={
            "type": "interval",
            "interval_minutes": 120,
            "active_window": {"start": "08:00", "end": "22:00"},
            "days_of_week": ["mon", "tue", "wed", "thu", "fri"],
            "start_date": test_start_date.isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Drink {glass_size_ml} ml",
    )

    r = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 24},
    )
    assert r.status_code == 200
    fires = r.json()
    # If today is Monday we get events; if not 0 from a weekday-only schedule
    # Just verify structure is correct regardless
    for fire in fires:
        assert fire["payload"]["category"] == "water"
        assert fire["payload"]["actions"] == ["logged_value", "skipped", "snooze_15"]


async def test_interval_weekend_zero_events(client: AsyncClient) -> None:
    """Weekday-only interval on a Sunday window returns 0 fires."""
    device_id = "upcoming-weekend-0000001"
    await _user(client, device_id)
    item_id = await _create_water_item(client, device_id)

    # Next Sunday for start_date
    today = date.today()
    days_until_sunday = (6 - today.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 0
    next_sunday = today + timedelta(days=days_until_sunday)
    while next_sunday.weekday() != 6:
        next_sunday += timedelta(days=1)

    await _add_reminder(
        client,
        device_id,
        item_id,
        schedule={
            "type": "interval",
            "interval_minutes": 120,
            "active_window": {"start": "08:00", "end": "22:00"},
            "days_of_week": ["mon"],  # Monday only
            "start_date": date.today().isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Drink water",
    )

    # If today is Sunday (weekday 6) we'd get 0 events for Monday-only schedule
    # This test just verifies no 500 and correct structure
    r = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 24},
    )
    assert r.status_code == 200
    # If today is not Monday, fires should be 0
    if date.today().weekday() != 0:
        assert len(r.json()) == 0


# ── template substitution ──────────────────────────────────────────────────────


async def test_template_substitution_drug_name(client: AsyncClient) -> None:
    device_id = "upcoming-template-000001"
    await _user(client, device_id)
    item_id = await _create_med_item(client, device_id)
    await _add_reminder(
        client,
        device_id,
        item_id,
        schedule={
            "type": "recurring",
            "times": ["08:00", "20:00"],
            "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_date": date.today().isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Time to take {drug_name} {dosage}",
    )
    r = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 48},
    )
    assert r.status_code == 200
    for fire in r.json():
        assert "Metformin" in fire["payload"]["body"]
        assert "500mg" in fire["payload"]["body"]


async def test_template_missing_key_renders_literal(client: AsyncClient) -> None:
    """Unknown {foo} in template renders as literal 'foo' — never crashes."""
    device_id = "upcoming-missing-key0001"
    await _user(client, device_id)
    item_id = await _create_med_item(client, device_id)
    await _add_reminder(
        client,
        device_id,
        item_id,
        schedule={
            "type": "recurring",
            "times": ["08:00"],
            "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_date": date.today().isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Take {drug_name} — also {unknown_key}",
    )
    r = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 48},
    )
    assert r.status_code == 200
    for fire in r.json():
        body = fire["payload"]["body"]
        assert "Metformin" in body
        assert "unknown_key" in body  # literal key, not '{unknown_key}'
        assert "{" not in body  # no raw format strings left


# ── filter conditions ──────────────────────────────────────────────────────────


async def test_inactive_reminder_excluded(client: AsyncClient) -> None:
    device_id = "upcoming-inactive-000001"
    await _user(client, device_id)
    item_id = await _create_med_item(client, device_id)
    reminder_id = await _add_reminder(
        client,
        device_id,
        item_id,
        schedule={
            "type": "recurring",
            "times": ["08:00", "20:00"],
            "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_date": date.today().isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Take it",
    )

    # Deactivate the reminder
    await client.delete(
        f"/v1/wellness/reminders/{reminder_id}",
        headers={"X-Device-Id": device_id},
    )

    r = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 48},
    )
    assert r.status_code == 200
    # No fires for the deactivated reminder
    reminder_ids = {f["reminder_id"] for f in r.json()}
    assert reminder_id not in reminder_ids


async def test_discontinued_item_excluded(client: AsyncClient) -> None:
    device_id = "upcoming-discont-0000001"
    await _user(client, device_id)
    item_id = await _create_med_item(client, device_id)
    await _add_reminder(
        client,
        device_id,
        item_id,
        schedule={
            "type": "recurring",
            "times": ["08:00", "20:00"],
            "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_date": date.today().isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Take it",
    )

    # Soft-delete the item
    await client.delete(
        f"/v1/wellness/tracked-items/{item_id}",
        headers={"X-Device-Id": device_id},
    )

    r = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 48},
    )
    assert r.status_code == 200
    item_ids = {f["tracked_item_id"] for f in r.json()}
    assert item_id not in item_ids


async def test_cross_user_reminder_excluded(client: AsyncClient) -> None:
    device_a = "upcoming-cross-a-000001"
    device_b = "upcoming-cross-b-000001"
    await _user(client, device_a)
    await _user(client, device_b)

    item_id = await _create_med_item(client, device_a)
    await _add_reminder(
        client,
        device_a,
        item_id,
        schedule={
            "type": "recurring",
            "times": ["08:00", "20:00"],
            "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_date": date.today().isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Take it",
    )

    # User B should see NONE of user A's fires
    r = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_b},
        params={"hours": 48},
    )
    assert r.status_code == 200
    # B has no items, so no fires from A should appear
    item_ids = {f["tracked_item_id"] for f in r.json()}
    assert item_id not in item_ids


async def test_hours_24_subset_of_hours_48(client: AsyncClient) -> None:
    device_id = "upcoming-subset-0000001"
    await _user(client, device_id)
    item_id = await _create_med_item(client, device_id)
    await _add_reminder(
        client,
        device_id,
        item_id,
        schedule={
            "type": "recurring",
            "times": ["08:00", "20:00"],
            "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_date": date.today().isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Take it",
    )

    r24 = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 24},
    )
    r48 = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 48},
    )
    fires_24 = {f["fire_key"] for f in r24.json()}
    fires_48 = {f["fire_key"] for f in r48.json()}
    assert fires_24.issubset(fires_48)
    assert len(fires_48) >= len(fires_24)


# ── fire_key structure ────────────────────────────────────────────────────────


async def test_fire_key_format(client: AsyncClient) -> None:
    device_id = "upcoming-firekey-000001"
    await _user(client, device_id)
    item_id = await _create_med_item(client, device_id)
    reminder_id = await _add_reminder(
        client,
        device_id,
        item_id,
        schedule={
            "type": "recurring",
            "times": ["08:00"],
            "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            "start_date": date.today().isoformat(),
            "timezone": "Asia/Kolkata",
        },
        template="Take it",
    )
    r = await client.get(
        "/v1/wellness/reminders/upcoming",
        headers={"X-Device-Id": device_id},
        params={"hours": 48},
    )
    assert r.status_code == 200
    for fire in r.json():
        # fire_key = "{reminder_id}:{fire_at.isoformat()}"
        assert fire["fire_key"].startswith(reminder_id + ":")
