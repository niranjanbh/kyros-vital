"""User B — Rajesh, 58, hypertension + T2D, 240 days of data."""

from __future__ import annotations

import random
import uuid
from datetime import timedelta
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
    now_ist,
)

# Stress week: day -120 to day -113 relative to today
_STRESS_START_DAYS_AGO = 120
_STRESS_END_DAYS_AGO = 113


def _in_stress_week(dt: Any) -> bool:
    stress_start = days_ago(_STRESS_START_DAYS_AGO)
    stress_end = days_ago(_STRESS_END_DAYS_AGO) + timedelta(days=1)
    return stress_start <= dt < stress_end


async def seed(db: AsyncSession) -> uuid.UUID:
    random.seed(43)  # different seed per user for variety

    # ── User ──────────────────────────────────────────────────────────────────
    user = User(
        device_id="demo-seed-rajesh",
        email="rajesh.demo@kyros.local",
        name="Rajesh",
        age=58,
        gender="male",
        timezone="Asia/Kolkata",
    )
    db.add(user)
    await db.flush()
    uid = user.id

    start = days_ago(240)
    today_dt = days_ago(0)
    today_str = today_dt.date().isoformat()
    start_str = start.date().isoformat()

    # ── Tracked items ─────────────────────────────────────────────────────────
    amlodipine = TrackedItem(
        user_id=uid, category="medication", name="Amlodipine 5mg",
        item_metadata={"drug_name": "Amlodipine", "dosage": "5 mg", "form": "tablet",
                       "with_food": False},
        start_date=start.date(), source="demo_seed",
    )
    db.add(amlodipine)

    telmisartan = TrackedItem(
        user_id=uid, category="medication", name="Telmisartan 40mg",
        item_metadata={"drug_name": "Telmisartan", "dosage": "40 mg", "form": "tablet",
                       "with_food": False},
        start_date=start.date(), source="demo_seed",
    )
    db.add(telmisartan)

    metformin = TrackedItem(
        user_id=uid, category="medication", name="Metformin 1g",
        item_metadata={"drug_name": "Metformin", "dosage": "1 g", "form": "tablet",
                       "with_food": True},
        start_date=start.date(), source="demo_seed",
    )
    db.add(metformin)

    atorvastatin = TrackedItem(
        user_id=uid, category="medication", name="Atorvastatin 10mg",
        item_metadata={"drug_name": "Atorvastatin", "dosage": "10 mg", "form": "tablet",
                       "with_food": False},
        start_date=start.date(), source="demo_seed",
    )
    db.add(atorvastatin)

    water = TrackedItem(
        user_id=uid, category="water", name="Daily Hydration",
        item_metadata={"daily_target_ml": 3000, "glass_size_ml": 300},
        start_date=start.date(), source="demo_seed",
    )
    db.add(water)
    await db.flush()

    # ── Reminders ─────────────────────────────────────────────────────────────
    amlodipine_rem = Reminder(
        tracked_item_id=amlodipine.id,
        schedule={"type": "recurring", "times": ["08:00"], "days_of_week": ALL_DAYS,
                  "start_date": start_str, "end_date": None, "timezone": "Asia/Kolkata"},
        message_template="Take {drug_name} {dosage}", channels=["in_app"],
    )
    db.add(amlodipine_rem)

    telmisartan_rem = Reminder(
        tracked_item_id=telmisartan.id,
        schedule={"type": "recurring", "times": ["08:00"], "days_of_week": ALL_DAYS,
                  "start_date": start_str, "end_date": None, "timezone": "Asia/Kolkata"},
        message_template="Take {drug_name} {dosage}", channels=["in_app"],
    )
    db.add(telmisartan_rem)

    metformin_rem = Reminder(
        tracked_item_id=metformin.id,
        schedule={"type": "recurring", "times": ["08:00", "20:00"], "days_of_week": ALL_DAYS,
                  "start_date": start_str, "end_date": None, "timezone": "Asia/Kolkata"},
        message_template="Take {drug_name} {dosage}", channels=["in_app"],
    )
    db.add(metformin_rem)

    atorvastatin_rem = Reminder(
        tracked_item_id=atorvastatin.id,
        schedule={"type": "recurring", "times": ["22:00"], "days_of_week": ALL_DAYS,
                  "start_date": start_str, "end_date": None, "timezone": "Asia/Kolkata"},
        message_template="Take {drug_name} {dosage}", channels=["in_app"],
    )
    db.add(atorvastatin_rem)

    water_rem = Reminder(
        tracked_item_id=water.id,
        schedule={"type": "interval", "interval_minutes": 120,
                  "active_window": {"start": "06:00", "end": "22:00"},
                  "days_of_week": ALL_DAYS, "timezone": "Asia/Kolkata"},
        message_template="Drink {glass_size_ml} ml of water", channels=["in_app"],
    )
    db.add(water_rem)
    await db.flush()

    # ── Log entries ───────────────────────────────────────────────────────────
    logs: list[dict[str, Any]] = []

    def _w(normal: dict[str, float], fire_dt: Any) -> dict[str, float]:
        """Override with stress-week weights if applicable."""
        if _in_stress_week(fire_dt):
            return {"taken": 0.25, "skipped": 0.15, "missed": 0.60}
        return normal

    # Amlodipine: 91%
    for fire in generate_fires_recurring(start, today_dt, ["08:00"], ALL_DAYS):
        action = weighted_action(_w({"taken": 0.91, "skipped": 0.05, "missed": 0.04}, fire))
        if action:
            jitter = random.randint(-15, 25) if action == "taken" else random.randint(30, 120)
            logs.append(log_entry_dict(uid, amlodipine.id, amlodipine_rem.id,
                                       make_fire_key(amlodipine_rem.id, fire),
                                       action, jittered_time(fire, jitter, jitter)))

    # Telmisartan: 88%
    for fire in generate_fires_recurring(start, today_dt, ["08:00"], ALL_DAYS):
        action = weighted_action(_w({"taken": 0.88, "skipped": 0.07, "missed": 0.05}, fire))
        if action:
            jitter = random.randint(-15, 25) if action == "taken" else random.randint(30, 120)
            logs.append(log_entry_dict(uid, telmisartan.id, telmisartan_rem.id,
                                       make_fire_key(telmisartan_rem.id, fire),
                                       action, jittered_time(fire, jitter, jitter)))

    # Metformin morning: 84%
    for fire in generate_fires_recurring(start, today_dt, ["08:00"], ALL_DAYS):
        action = weighted_action(_w({"taken": 0.84, "skipped": 0.08, "missed": 0.08}, fire))
        if action:
            jitter = random.randint(-15, 25) if action == "taken" else random.randint(30, 120)
            logs.append(log_entry_dict(uid, metformin.id, metformin_rem.id,
                                       make_fire_key(metformin_rem.id, fire),
                                       action, jittered_time(fire, jitter, jitter)))

    # Metformin evening: 65% (evening dropoff)
    for fire in generate_fires_recurring(start, today_dt, ["20:00"], ALL_DAYS):
        action = weighted_action(_w({"taken": 0.65, "skipped": 0.15, "missed": 0.20}, fire))
        if action:
            jitter = random.randint(-15, 25) if action == "taken" else random.randint(30, 180)
            logs.append(log_entry_dict(uid, metformin.id, metformin_rem.id,
                                       make_fire_key(metformin_rem.id, fire),
                                       action, jittered_time(fire, jitter, jitter)))

    # Atorvastatin 10pm: 65%
    for fire in generate_fires_recurring(start, today_dt, ["22:00"], ALL_DAYS):
        action = weighted_action(_w({"taken": 0.65, "skipped": 0.10, "missed": 0.25}, fire))
        if action:
            jitter = random.randint(-15, 25) if action == "taken" else random.randint(30, 120)
            logs.append(log_entry_dict(uid, atorvastatin.id, atorvastatin_rem.id,
                                       make_fire_key(atorvastatin_rem.id, fire),
                                       action, jittered_time(fire, jitter, jitter)))

    # Water: 40% per fire
    for fire in generate_fires_interval(start, today_dt, 120, "06:00", "22:00", ALL_DAYS):
        action = weighted_action({"logged_value": 0.40, "missed": 0.60})
        if action:
            jitter = random.randint(0, 10)
            logs.append(log_entry_dict(uid, water.id, water_rem.id,
                                       make_fire_key(water_rem.id, fire),
                                       "logged_value", jittered_time(fire, jitter, jitter)))

    if logs:
        await db.execute(insert(LogEntry), logs)
        await db.flush()

    # ── Measurements ──────────────────────────────────────────────────────────
    measurements: list[dict[str, Any]] = []

    # BP: daily, 240 readings
    stress_start_days = _STRESS_START_DAYS_AGO
    stress_end_days = _STRESS_END_DAYS_AGO

    for i in range(240):
        day_offset = 240 - i  # 240, 239, ... 1
        if day_offset == 0:
            day_offset = 1
        measured_at = days_ago(day_offset).replace(hour=7, minute=random.randint(0, 15))
        if measured_at > now_ist():
            continue

        in_stress = stress_end_days <= day_offset <= stress_start_days
        recovery_days = max(0, stress_end_days - day_offset)  # days after stress ended

        if in_stress:
            systolic = round(random.uniform(158, 168), 0)
            diastolic = round(random.uniform(96, 104), 0)
        elif recovery_days < 30:
            # Gradual recovery over 30 days
            factor = recovery_days / 30.0
            systolic = round(random.uniform(
                158 - factor * (158 - 138),
                168 - factor * (168 - 148),
            ), 0)
            diastolic = round(random.uniform(
                96 - factor * (96 - 86),
                104 - factor * (104 - 94),
            ), 0)
        else:
            systolic = round(random.uniform(138, 148), 0)
            diastolic = round(random.uniform(86, 94), 0)

        measurements.append(measurement_dict(uid, "bp_systolic", systolic, "mmHg", measured_at,
                                              reference_range={"low": 90, "high": 130}))
        measurements.append(measurement_dict(uid, "bp_diastolic", diastolic, "mmHg", measured_at,
                                              reference_range={"low": 60, "high": 85}))

    # Weight: weekly, 84–86 kg
    for i in range(240 // 7):
        day_offset = max(1, 240 - i * 7)
        measured_at = days_ago(day_offset).replace(hour=7, minute=0)
        if measured_at > now_ist():
            continue
        value = round(random.uniform(83.4, 86.6), 1)
        measurements.append(measurement_dict(uid, "weight", value, "kg", measured_at,
                                              reference_range={"low": 60, "high": 100}))

    # Fasting glucose: every 30 days, improving
    glucose_schedule = [
        (240, 128.0), (210, 125.0), (180, 122.0), (150, 119.0),
        (120, 118.0), (90, 116.0), (60, 115.0), (30, 113.0),
    ]
    for day_offset, base_val in glucose_schedule:
        measured_at = days_ago(day_offset).replace(hour=7, minute=0)
        if measured_at > now_ist():
            continue
        val = round(base_val + random.uniform(-3, 3), 1)
        measurements.append(measurement_dict(uid, "fasting_glucose", val, "mg/dL", measured_at,
                                              reference_range={"low": 70, "high": 100}))

    if measurements:
        await db.execute(insert(Measurement), measurements)
        await db.flush()

    # ── Lab reports ───────────────────────────────────────────────────────────
    reports = [
        LabReport(
            user_id=uid, report_date=days_ago(240).date(), lab_name="Thyrocare",
            note="Demo data, no file attached",
            parsed=[
                parsed_test("HbA1c", "8.4", "%", None, 7.0, "high"),
                parsed_test("Fasting Glucose", "142", "mg/dL", 70, 100, "high"),
                parsed_test("Total Cholesterol", "228", "mg/dL", None, 200, "high"),
                parsed_test("LDL", "142", "mg/dL", None, 130, "high"),
                parsed_test("HDL", "38", "mg/dL", 40, None, "low"),
                parsed_test("Triglycerides", "192", "mg/dL", None, 150, "high"),
                parsed_test("Creatinine", "1.1", "mg/dL", 0.6, 1.2, "normal"),
                parsed_test("eGFR", "78", "mL/min/1.73m²", 60, None, "normal"),
                parsed_test("ALT", "32", "U/L", None, 40, "normal"),
                parsed_test("AST", "28", "U/L", None, 40, "normal"),
            ],
        ),
        LabReport(
            user_id=uid, report_date=days_ago(180).date(), lab_name="SRL Diagnostics",
            note="Demo data, no file attached",
            parsed=[
                parsed_test("HbA1c", "8.1", "%", None, 7.0, "high"),
                parsed_test("Fasting Glucose", "135", "mg/dL", 70, 100, "high"),
                parsed_test("Total Cholesterol", "210", "mg/dL", None, 200, "high"),
                parsed_test("LDL", "128", "mg/dL", None, 130, "normal"),
                parsed_test("HDL", "40", "mg/dL", 40, None, "normal"),
                parsed_test("Triglycerides", "168", "mg/dL", None, 150, "high"),
                parsed_test("Creatinine", "1.1", "mg/dL", 0.6, 1.2, "normal"),
                parsed_test("eGFR", "76", "mL/min/1.73m²", 60, None, "normal"),
                parsed_test("ALT", "30", "U/L", None, 40, "normal"),
                parsed_test("AST", "27", "U/L", None, 40, "normal"),
            ],
        ),
        LabReport(
            user_id=uid, report_date=days_ago(120).date(), lab_name="Thyrocare",
            note="Demo data, no file attached",
            parsed=[
                parsed_test("HbA1c", "7.9", "%", None, 7.0, "high"),
                parsed_test("Fasting Glucose", "126", "mg/dL", 70, 100, "high"),
                parsed_test("Total Cholesterol", "196", "mg/dL", None, 200, "normal"),
                parsed_test("LDL", "118", "mg/dL", None, 130, "normal"),
                parsed_test("HDL", "42", "mg/dL", 40, None, "normal"),
                parsed_test("Triglycerides", "148", "mg/dL", None, 150, "normal"),
                parsed_test("Creatinine", "1.2", "mg/dL", 0.6, 1.2, "normal"),
                parsed_test("eGFR", "75", "mL/min/1.73m²", 60, None, "normal"),
                parsed_test("ALT", "58", "U/L", None, 40, "high"),  # incidental finding
                parsed_test("AST", "34", "U/L", None, 40, "normal"),
            ],
        ),
        LabReport(
            user_id=uid, report_date=days_ago(60).date(), lab_name="SRL Diagnostics",
            note="Demo data, no file attached",
            parsed=[
                parsed_test("HbA1c", "7.6", "%", None, 7.0, "high"),
                parsed_test("Fasting Glucose", "118", "mg/dL", 70, 100, "high"),
                parsed_test("Total Cholesterol", "188", "mg/dL", None, 200, "normal"),
                parsed_test("LDL", "108", "mg/dL", None, 130, "normal"),
                parsed_test("HDL", "44", "mg/dL", 40, None, "normal"),
                parsed_test("Creatinine", "1.2", "mg/dL", 0.6, 1.2, "normal"),
                parsed_test("eGFR", "73", "mL/min/1.73m²", 60, None, "normal"),
                parsed_test("ALT", "38", "U/L", None, 40, "normal"),
            ],
        ),
        LabReport(
            user_id=uid, report_date=days_ago(15).date(), lab_name="Thyrocare",
            note="Demo data, no file attached",
            parsed=[
                parsed_test("HbA1c", "7.2", "%", None, 7.0, "high"),
                parsed_test("Fasting Glucose", "112", "mg/dL", 70, 100, "high"),
                parsed_test("Total Cholesterol", "176", "mg/dL", None, 200, "normal"),
                parsed_test("LDL", "96", "mg/dL", None, 130, "normal"),
                parsed_test("HDL", "46", "mg/dL", 40, None, "normal"),
                parsed_test("Triglycerides", "134", "mg/dL", None, 150, "normal"),
                parsed_test("Creatinine", "1.3", "mg/dL", 0.6, 1.2, "high"),
                parsed_test("eGFR", "72", "mL/min/1.73m²", 60, None, "normal"),
                parsed_test("ALT", "36", "U/L", None, 40, "normal"),
                parsed_test("AST", "30", "U/L", None, 40, "normal"),
            ],
        ),
    ]
    for r in reports:
        db.add(r)

    await db.flush()
    return uid
