"""User A — Priya, 42, hypothyroid + early PCOS, 180 days of data."""

from __future__ import annotations

import random
import uuid
from datetime import date, timedelta
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
    IST,
    days_ago,
    generate_fires_interval,
    generate_fires_recurring,
    jittered_time,
    log_entry_dict,
    make_fire_key,
    measurement_dict,
    parsed_test,
    weighted_action,
)


async def seed(db: AsyncSession) -> uuid.UUID:
    random.seed(42)

    # ── User ──────────────────────────────────────────────────────────────────
    user = User(
        device_id="demo-seed-priya",
        email="priya.demo@kyros.local",
        name="Priya",
        age=42,
        gender="female",
        timezone="Asia/Kolkata",
    )
    db.add(user)
    await db.flush()
    uid = user.id

    start_180 = days_ago(180)
    start_90 = days_ago(90)
    today_dt = days_ago(0)

    # ── Tracked items ─────────────────────────────────────────────────────────
    levo = TrackedItem(
        user_id=uid, category="medication", name="Levothyroxine 75mcg",
        item_metadata={"drug_name": "Levothyroxine", "dosage": "75 mcg", "form": "tablet",
                       "with_food": False, "instructions": "30 min before breakfast"},
        start_date=start_180.date(), source="demo_seed",
    )
    db.add(levo)
    await db.flush()

    met = TrackedItem(
        user_id=uid, category="medication", name="Metformin 500mg",
        item_metadata={"drug_name": "Metformin", "dosage": "500 mg", "form": "tablet",
                       "with_food": True},
        start_date=start_180.date(), source="demo_seed",
    )
    db.add(met)
    await db.flush()

    inositol = TrackedItem(
        user_id=uid, category="medication", name="Myo-Inositol 2g",
        item_metadata={"drug_name": "Myo-Inositol", "dosage": "2 g", "form": "powder"},
        start_date=start_90.date(), source="demo_seed",
    )
    db.add(inositol)
    await db.flush()

    water = TrackedItem(
        user_id=uid, category="water", name="Daily Hydration",
        item_metadata={"daily_target_ml": 2500, "glass_size_ml": 250},
        start_date=start_180.date(), source="demo_seed",
    )
    db.add(water)
    await db.flush()

    vitals = TrackedItem(
        user_id=uid, category="vital_check", name="Vitals Tracking",
        item_metadata={"notes": "TSH, weight, BP monitoring"},
        start_date=start_180.date(), source="demo_seed",
    )
    db.add(vitals)
    await db.flush()

    # ── Reminders ─────────────────────────────────────────────────────────────
    today_str = today_dt.date().isoformat()
    start_180_str = start_180.date().isoformat()
    start_90_str = start_90.date().isoformat()

    levo_rem = Reminder(
        tracked_item_id=levo.id,
        schedule={"type": "recurring", "times": ["06:30"], "days_of_week": ALL_DAYS,
                  "start_date": start_180_str, "end_date": None, "timezone": "Asia/Kolkata"},
        message_template="Take {drug_name} {dosage}", channels=["in_app"],
    )
    db.add(levo_rem)

    met_rem = Reminder(
        tracked_item_id=met.id,
        schedule={"type": "recurring", "times": ["09:00", "21:00"], "days_of_week": ALL_DAYS,
                  "start_date": start_180_str, "end_date": None, "timezone": "Asia/Kolkata"},
        message_template="Take {drug_name} {dosage}", channels=["in_app"],
    )
    db.add(met_rem)

    inositol_rem = Reminder(
        tracked_item_id=inositol.id,
        schedule={"type": "recurring", "times": ["09:00"], "days_of_week": ALL_DAYS,
                  "start_date": start_90_str, "end_date": None, "timezone": "Asia/Kolkata"},
        message_template="Take {drug_name} {dosage}", channels=["in_app"],
    )
    db.add(inositol_rem)

    water_rem = Reminder(
        tracked_item_id=water.id,
        schedule={"type": "interval", "interval_minutes": 120,
                  "active_window": {"start": "08:00", "end": "22:00"},
                  "days_of_week": ALL_DAYS, "timezone": "Asia/Kolkata"},
        message_template="Drink {glass_size_ml} ml of water", channels=["in_app"],
    )
    db.add(water_rem)

    await db.flush()

    # ── Log entries ───────────────────────────────────────────────────────────
    logs: list[dict[str, Any]] = []

    # Levothyroxine: 95% taken, 3% skipped, 2% missed. Weekend: 90/7/3.
    levo_fires = generate_fires_recurring(start_180, today_dt, ["06:30"], ALL_DAYS)
    for fire in levo_fires:
        is_weekend = fire.weekday() >= 5
        w = ({"taken": 0.90, "skipped": 0.07, "missed": 0.03}
             if is_weekend else {"taken": 0.95, "skipped": 0.03, "missed": 0.02})
        action = weighted_action(w)
        if action:
            jitter = (random.randint(-15, 25) if action == "taken"
                      else random.randint(60, 180))
            logs.append(log_entry_dict(
                uid, levo.id, levo_rem.id,
                make_fire_key(levo_rem.id, fire),
                action, jittered_time(fire, jitter, jitter),
            ))

    # Metformin morning: 88/8/4
    met_morning_fires = generate_fires_recurring(start_180, today_dt, ["09:00"], ALL_DAYS)
    for fire in met_morning_fires:
        action = weighted_action({"taken": 0.88, "skipped": 0.08, "missed": 0.04})
        if action:
            jitter = random.randint(-15, 25) if action == "taken" else random.randint(60, 180)
            logs.append(log_entry_dict(
                uid, met.id, met_rem.id,
                make_fire_key(met_rem.id, fire),
                action, jittered_time(fire, jitter, jitter),
            ))

    # Metformin evening: 72/18/10
    met_evening_fires = generate_fires_recurring(start_180, today_dt, ["21:00"], ALL_DAYS)
    for fire in met_evening_fires:
        action = weighted_action({"taken": 0.72, "skipped": 0.18, "missed": 0.10})
        if action:
            jitter = random.randint(-15, 25) if action == "taken" else random.randint(60, 180)
            logs.append(log_entry_dict(
                uid, met.id, met_rem.id,
                make_fire_key(met_rem.id, fire),
                action, jittered_time(fire, jitter, jitter),
            ))

    # Inositol: 85/10/5
    inositol_fires = generate_fires_recurring(start_90, today_dt, ["09:00"], ALL_DAYS)
    for fire in inositol_fires:
        action = weighted_action({"taken": 0.85, "skipped": 0.10, "missed": 0.05})
        if action:
            jitter = random.randint(-15, 25) if action == "taken" else random.randint(60, 180)
            logs.append(log_entry_dict(
                uid, inositol.id, inositol_rem.id,
                make_fire_key(inositol_rem.id, fire),
                action, jittered_time(fire, jitter, jitter),
            ))

    # Water: ~30% logged per fire
    water_fires = generate_fires_interval(
        start_180, today_dt, 120, "08:00", "22:00", ALL_DAYS
    )
    for fire in water_fires:
        action = weighted_action({"logged_value": 0.30, "missed": 0.70})
        if action:
            jitter = random.randint(0, 10)
            logs.append(log_entry_dict(
                uid, water.id, water_rem.id,
                make_fire_key(water_rem.id, fire),
                "logged_value", jittered_time(fire, jitter, jitter),
            ))

    if logs:
        await db.execute(insert(LogEntry), logs)
        await db.flush()

    # ── Measurements ──────────────────────────────────────────────────────────
    measurements: list[dict[str, Any]] = []

    # Weight: every 7 days, 78.4 → 74.1 kg over 180 days (~26 readings)
    n_weight = 180 // 7
    for i in range(n_weight):
        day_offset = 180 - (i * 7)
        if day_offset < 0:
            break
        base = 78.4 - (4.3 / n_weight) * i
        # Occasional plateau (weeks 8–11)
        if 8 <= i <= 11:
            base += 0.3
        value = round(base + random.uniform(-0.4, 0.4), 1)
        measured_at = days_ago(day_offset).replace(hour=7, minute=random.randint(0, 30))
        measurements.append(measurement_dict(uid, "weight", value, "kg", measured_at,
                                              reference_range={"low": 60, "high": 85}))

    # BP: every 14 days, systolic 118–128, diastolic 78–84
    for i in range(180 // 14):
        day_offset = 180 - (i * 14)
        if day_offset < 0:
            break
        measured_at = days_ago(day_offset).replace(hour=8, minute=random.randint(0, 20))
        systolic = round(random.uniform(118, 128), 0)
        diastolic = round(random.uniform(78, 84), 0)
        measurements.append(measurement_dict(uid, "bp_systolic", systolic, "mmHg", measured_at,
                                              reference_range={"low": 90, "high": 130}))
        measurements.append(measurement_dict(uid, "bp_diastolic", diastolic, "mmHg", measured_at,
                                              reference_range={"low": 60, "high": 85}))

    # Fasting glucose: 5 readings spread over 180 days
    glucose_days = [180, 135, 90, 45, 10]
    glucose_vals = [102.0, 99.0, 97.0, 95.0, 94.0]
    for day_offset, val in zip(glucose_days, glucose_vals):
        measured_at = days_ago(day_offset).replace(hour=7, minute=0)
        val_j = round(val + random.uniform(-2, 2), 1)
        measurements.append(measurement_dict(uid, "fasting_glucose", val_j, "mg/dL", measured_at,
                                              reference_range={"low": 70, "high": 100}))

    if measurements:
        await db.execute(insert(Measurement), measurements)
        await db.flush()

    # ── Lab reports ───────────────────────────────────────────────────────────
    reports = [
        # Report 1 (day -180): TSH high, Vit D low
        LabReport(
            user_id=uid, report_date=days_ago(180).date(), lab_name="Thyrocare",
            note="Demo data, no file attached",
            parsed=[
                parsed_test("TSH", "8.2", "mIU/L", 0.4, 4.0, "high"),
                parsed_test("Free T4", "0.7", "ng/dL", 0.8, 1.8, "low"),
                parsed_test("Fasting Glucose", "102", "mg/dL", 70, 100, "high"),
                parsed_test("HbA1c", "5.7", "%", None, 5.7, "high"),
                parsed_test("Total Cholesterol", "198", "mg/dL", None, 200, "normal"),
                parsed_test("LDL", "118", "mg/dL", None, 130, "normal"),
                parsed_test("HDL", "52", "mg/dL", 45, None, "normal"),
                parsed_test("Triglycerides", "142", "mg/dL", None, 150, "normal"),
                parsed_test("Vitamin D", "18", "ng/mL", 20, 50, "low"),
                parsed_test("Vitamin B12", "380", "pg/mL", 200, 900, "normal"),
            ],
        ),
        # Report 2 (day -120): TSH improving
        LabReport(
            user_id=uid, report_date=days_ago(120).date(), lab_name="SRL Diagnostics",
            note="Demo data, no file attached",
            parsed=[
                parsed_test("TSH", "4.1", "mIU/L", 0.4, 4.0, "high"),
                parsed_test("Free T4", "1.1", "ng/dL", 0.8, 1.8, "normal"),
                parsed_test("HbA1c", "5.6", "%", None, 5.7, "normal"),
            ],
        ),
        # Report 3 (day -60): TSH normal, Vit D corrected
        LabReport(
            user_id=uid, report_date=days_ago(60).date(), lab_name="Thyrocare",
            note="Demo data, no file attached",
            parsed=[
                parsed_test("TSH", "3.2", "mIU/L", 0.4, 4.0, "normal"),
                parsed_test("Free T4", "1.3", "ng/dL", 0.8, 1.8, "normal"),
                parsed_test("Fasting Glucose", "94", "mg/dL", 70, 100, "normal"),
                parsed_test("HbA1c", "5.5", "%", None, 5.7, "normal"),
                parsed_test("Vitamin D", "32", "ng/mL", 20, 50, "normal"),
            ],
        ),
        # Report 4 (day -10): All improving
        LabReport(
            user_id=uid, report_date=days_ago(10).date(), lab_name="SRL Diagnostics",
            note="Demo data, no file attached",
            parsed=[
                parsed_test("TSH", "2.8", "mIU/L", 0.4, 4.0, "normal"),
                parsed_test("Free T4", "1.4", "ng/dL", 0.8, 1.8, "normal"),
                parsed_test("HbA1c", "5.4", "%", None, 5.7, "normal"),
                parsed_test("Total Cholesterol", "184", "mg/dL", None, 200, "normal"),
                parsed_test("LDL", "108", "mg/dL", None, 130, "normal"),
                parsed_test("HDL", "55", "mg/dL", 45, None, "normal"),
            ],
        ),
    ]
    for r in reports:
        db.add(r)

    await db.flush()

    return uid
