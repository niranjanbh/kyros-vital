"""Seed the database with demo data for local development."""

import asyncio
from datetime import date

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.shared.models.user import User
from app.wellness.models.log_entry import LogEntry  # noqa: F401 — ensure model registered
from app.wellness.models.measurement import Measurement  # noqa: F401
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem

TODAY = date.today().isoformat()

MEDICATION_SCHEDULE = {
    "type": "recurring",
    "times": ["08:00", "20:00"],
    "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    "start_date": TODAY,
    "end_date": None,
    "timezone": "Asia/Kolkata",
}

WATER_SCHEDULE = {
    "type": "interval",
    "interval_minutes": 120,
    "active_window": {"start": "08:00", "end": "22:00"},
    "days_of_week": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
    "timezone": "Asia/Kolkata",
}

WORKOUT_SCHEDULE = {
    "type": "recurring",
    "times": ["07:00"],
    "days_of_week": ["mon", "wed", "fri"],
    "start_date": TODAY,
    "end_date": None,
    "timezone": "Asia/Kolkata",
}


async def main() -> None:
    async with AsyncSessionLocal() as session:
        # ── User ─────────────────────────────────────────────────────────────
        device_id = "seed-device-abc12345"
        result = await session.execute(select(User).where(User.device_id == device_id))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(device_id=device_id, timezone="Asia/Kolkata")
            session.add(user)
            await session.flush()
        print(f"User: {user.id}  device_id={user.device_id}")

        # ── Medication ───────────────────────────────────────────────────────
        med = TrackedItem(
            user_id=user.id,
            category="medication",
            name="Metformin 500mg",
            item_metadata={
                "drug_name": "Metformin",
                "dosage": "500mg",
                "form": "tablet",
                "with_food": True,
                "instructions": "Take with meals",
            },
            start_date=date.today(),
        )
        session.add(med)
        await session.flush()

        med_reminder = Reminder(
            tracked_item_id=med.id,
            schedule=MEDICATION_SCHEDULE,
            message_template="Time to take {drug_name} {dosage}",
            channels=["in_app"],
        )
        session.add(med_reminder)
        print(f"TrackedItem (medication): {med.id}  name={med.name!r}")

        # ── Water ────────────────────────────────────────────────────────────
        water = TrackedItem(
            user_id=user.id,
            category="water",
            name="Daily Hydration",
            item_metadata={"daily_target_ml": 2500, "glass_size_ml": 250},
            start_date=date.today(),
        )
        session.add(water)
        await session.flush()

        water_reminder = Reminder(
            tracked_item_id=water.id,
            schedule=WATER_SCHEDULE,
            message_template="Drink a glass of water (250 ml)",
            channels=["in_app"],
        )
        session.add(water_reminder)
        print(f"TrackedItem (water): {water.id}  name={water.name!r}")

        # ── Workout ──────────────────────────────────────────────────────────
        workout = TrackedItem(
            user_id=user.id,
            category="workout",
            name="Strength Training",
            item_metadata={
                "workout_type": "Strength",
                "duration_minutes": 45,
                "location": "Gym",
            },
            start_date=date.today(),
        )
        session.add(workout)
        await session.flush()

        workout_reminder = Reminder(
            tracked_item_id=workout.id,
            schedule=WORKOUT_SCHEDULE,
            message_template="Time for your {workout_type} session — {duration_minutes} min",
            channels=["in_app"],
        )
        session.add(workout_reminder)
        print(f"TrackedItem (workout): {workout.id}  name={workout.name!r}")

        await session.commit()
        print("\nSeed complete.")


if __name__ == "__main__":
    asyncio.run(main())
