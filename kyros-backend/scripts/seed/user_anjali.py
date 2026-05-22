"""User C — Anjali, 29, fitness-focused, 21 days of sparse data."""

from __future__ import annotations

import random
import uuid
from typing import Any

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.wellness.models.lab_report import LabReport
from app.wellness.models.log_entry import LogEntry
from app.wellness.models.measurement import Measurement
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem
from app.shared.models.user import User
from scripts.seed.common import (
    ALL_DAYS,
    days_ago,
    generate_fires_interval,
    generate_fires_recurring,
    jittered_time,
    log_entry_dict,
    make_fire_key,
    measurement_dict,
    parsed_test,
    weighted_action,
    now_ist,
)

_MWF = ["mon", "wed", "fri"]


async def seed(db: AsyncSession) -> uuid.UUID:
    random.seed(44)  # distinct seed per user

    # ── User ──────────────────────────────────────────────────────────────────
    user = User(
        device_id="demo-seed-anjali",
        email="anjali.demo@kyros.local",
        name="Anjali",
        age=29,
        gender="female",
        timezone="Asia/Kolkata",
    )
    db.add(user)
    await db.flush()
    uid = user.id

    start_21 = days_ago(21)
    start_10 = days_ago(10)
    today_dt = days_ago(0)
    start_21_str = start_21.date().isoformat()
    start_10_str = start_10.date().isoformat()

    # ── Tracked items ─────────────────────────────────────────────────────────
    water = TrackedItem(
        user_id=uid, category="water", name="Daily Hydration",
        item_metadata={"daily_target_ml": 2500, "glass_size_ml": 250},
        start_date=start_21.date(), source="demo_seed",
    )
    db.add(water)

    multivitamin = TrackedItem(
        user_id=uid, category="medication", name="Multivitamin",
        item_metadata={"drug_name": "Multivitamin", "dosage": "1 tablet", "form": "tablet",
                       "with_food": True},
        start_date=start_10.date(), source="demo_seed",
    )
    db.add(multivitamin)

    workout = TrackedItem(
        user_id=uid, category="workout", name="Strength Training",
        item_metadata={"workout_type": "Strength", "duration_minutes": 60, "location": "Gym"},
        start_date=start_21.date(), source="demo_seed",
    )
    db.add(workout)
    await db.flush()

    # ── Reminders ─────────────────────────────────────────────────────────────
    water_rem = Reminder(
        tracked_item_id=water.id,
        schedule={"type": "interval", "interval_minutes": 90,
                  "active_window": {"start": "07:00", "end": "22:00"},
                  "days_of_week": ALL_DAYS, "timezone": "Asia/Kolkata"},
        message_template="Drink {glass_size_ml} ml of water", channels=["in_app"],
    )
    db.add(water_rem)

    multi_rem = Reminder(
        tracked_item_id=multivitamin.id,
        schedule={"type": "recurring", "times": ["09:00"], "days_of_week": ALL_DAYS,
                  "start_date": start_10_str, "end_date": None, "timezone": "Asia/Kolkata"},
        message_template="Take {drug_name} {dosage}", channels=["in_app"],
    )
    db.add(multi_rem)

    workout_rem = Reminder(
        tracked_item_id=workout.id,
        schedule={"type": "recurring", "times": ["18:00"], "days_of_week": _MWF,
                  "start_date": start_21_str, "end_date": None, "timezone": "Asia/Kolkata"},
        message_template="Time for your {workout_type} session", channels=["in_app"],
    )
    db.add(workout_rem)
    await db.flush()

    # ── Log entries ───────────────────────────────────────────────────────────
    logs: list[dict[str, Any]] = []

    # Water: ~71% per fire (realistic 5/7 days hitting target across 10 fires/day)
    for fire in generate_fires_interval(start_21, today_dt, 90, "07:00", "22:00", ALL_DAYS):
        action = weighted_action({"logged_value": 0.71, "missed": 0.29})
        if action:
            jitter = random.randint(0, 15)
            logs.append(log_entry_dict(uid, water.id, water_rem.id,
                                       make_fire_key(water_rem.id, fire),
                                       "logged_value", jittered_time(fire, jitter, jitter)))

    # Multivitamin: 90% adherence in 10 days
    for fire in generate_fires_recurring(start_10, today_dt, ["09:00"], ALL_DAYS):
        action = weighted_action({"taken": 0.90, "skipped": 0.05, "missed": 0.05})
        if action:
            jitter = random.randint(-15, 25) if action == "taken" else random.randint(30, 90)
            logs.append(log_entry_dict(uid, multivitamin.id, multi_rem.id,
                                       make_fire_key(multi_rem.id, fire),
                                       action, jittered_time(fire, jitter, jitter)))

    # Workout: 80% (Mon/Wed/Fri)
    for fire in generate_fires_recurring(start_21, today_dt, ["18:00"], _MWF):
        action = weighted_action({"taken": 0.80, "skipped": 0.10, "missed": 0.10})
        if action:
            jitter = random.randint(-10, 20) if action == "taken" else random.randint(30, 120)
            logs.append(log_entry_dict(uid, workout.id, workout_rem.id,
                                       make_fire_key(workout_rem.id, fire),
                                       action, jittered_time(fire, jitter, jitter)))

    if logs:
        await db.execute(insert(LogEntry), logs)
        await db.flush()

    # ── Measurements ──────────────────────────────────────────────────────────
    measurements: list[dict[str, Any]] = []

    # Weight: 3 readings over 21 days
    for day_offset, val in [(21, 58.2), (10, 58.4), (2, 58.1)]:
        measured_at = days_ago(day_offset).replace(hour=7, minute=0)
        if measured_at > now_ist():
            continue
        measurements.append(measurement_dict(uid, "weight", val, "kg", measured_at,
                                              reference_range={"low": 45, "high": 80}))

    if measurements:
        await db.execute(insert(Measurement), measurements)
        await db.flush()

    # ── Lab report (1 report, all normal) ────────────────────────────────────
    report = LabReport(
        user_id=uid, report_date=days_ago(5).date(), lab_name="Thyrocare",
        note="Demo data, no file attached",
        parsed=[
            parsed_test("Haemoglobin", "13.8", "g/dL", 12.0, 17.5, "normal"),
            parsed_test("WBC", "6.2", "×10³/μL", 4.0, 11.0, "normal"),
            parsed_test("Platelets", "248", "×10³/μL", 150, 400, "normal"),
            parsed_test("Fasting Glucose", "86", "mg/dL", 70, 100, "normal"),
            parsed_test("Creatinine", "0.8", "mg/dL", 0.6, 1.1, "normal"),
            parsed_test("Sodium", "139", "mEq/L", 136, 145, "normal"),
            parsed_test("Potassium", "4.1", "mEq/L", 3.5, 5.0, "normal"),
            parsed_test("Vitamin D", "38", "ng/mL", 20, 50, "normal"),
            parsed_test("Iron", "92", "μg/dL", 60, 170, "normal"),
            parsed_test("TSH", "2.1", "mIU/L", 0.4, 4.0, "normal"),
        ],
    )
    db.add(report)
    await db.flush()

    return uid
