"""
Demo data seeding script.

Usage:
    poetry run python -m scripts.seed_demo
    poetry run python -m scripts.seed_demo --only priya
    poetry run python -m scripts.seed_demo --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from typing import Any

from sqlalchemy import func, select, text

DEMO_PREFIX = "demo-seed-"
MAX_NON_DEMO_USERS = 50


async def _safety_checks(db: Any) -> None:
    """Raise if the environment is production or the DB looks like it's non-dev."""
    env = os.environ.get("ENV", "development")
    if env == "production":
        raise RuntimeError("Refusing to seed demo data into production")

    from app.shared.models.user import User

    count_row = await db.execute(
        select(func.count()).select_from(User).where(
            ~User.device_id.like(f"{DEMO_PREFIX}%")
        )
    )
    non_demo_count: int = count_row.scalar_one()
    if non_demo_count > MAX_NON_DEMO_USERS:
        raise RuntimeError(
            f"Safety guard: found {non_demo_count} non-demo users "
            f"(max allowed: {MAX_NON_DEMO_USERS}). "
            "Are you pointing at the wrong database?"
        )


async def _wipe_demo_users(db: Any) -> None:
    """Delete all rows whose device_id starts with 'demo-seed-'. CASCADE handles the rest."""
    await db.execute(
        text(f"DELETE FROM users WHERE device_id LIKE '{DEMO_PREFIX}%'")
    )
    await db.flush()


async def _count_user_data(db: Any, user_id: Any) -> dict[str, int]:
    from app.wellness.models.lab_report import LabReport
    from app.wellness.models.log_entry import LogEntry
    from app.wellness.models.measurement import Measurement
    from app.wellness.models.reminder import Reminder
    from app.wellness.models.tracked_item import TrackedItem

    async def _cnt(model: Any, clause: Any) -> int:
        r = await db.execute(select(func.count()).select_from(model).where(clause))
        return r.scalar_one()

    return {
        "tracked_items": await _cnt(TrackedItem, TrackedItem.user_id == user_id),
        "reminders": await _cnt(Reminder, Reminder.tracked_item_id.in_(
            select(TrackedItem.id).where(TrackedItem.user_id == user_id)
        )),
        "log_entries": await _cnt(LogEntry, LogEntry.user_id == user_id),
        "measurements": await _cnt(Measurement, Measurement.user_id == user_id),
        "lab_reports": await _cnt(LabReport, LabReport.user_id == user_id),
    }


async def seed_all(
    only: str | None = None,
    dry_run: bool = False,
) -> dict[str, dict[str, int]]:
    """Seed all (or one) demo users. Returns counts per user."""
    from app.database import AsyncSessionLocal

    t0 = time.monotonic()

    async with AsyncSessionLocal() as db:
        await _safety_checks(db)

        if dry_run:
            print("DRY RUN — no changes will be written.")
            print(f"Would seed: {'all users' if not only else only}")
            return {}

        # Wipe existing demo data
        await _wipe_demo_users(db)

        stats: dict[str, dict[str, int]] = {}

        if only in (None, "priya"):
            from scripts.seed.user_priya import seed as seed_priya
            uid = await seed_priya(db)
            stats["Priya"] = await _count_user_data(db, uid)

        if only in (None, "rajesh"):
            from scripts.seed.user_rajesh import seed as seed_rajesh
            uid = await seed_rajesh(db)
            stats["Rajesh"] = await _count_user_data(db, uid)

        if only in (None, "anjali"):
            from scripts.seed.user_anjali import seed as seed_anjali
            uid = await seed_anjali(db)
            stats["Anjali"] = await _count_user_data(db, uid)

        await db.commit()

    elapsed = time.monotonic() - t0

    print("\nSeeded demo data:")
    for name, counts in stats.items():
        print(
            f"  {name:<8} 1 user, {counts['tracked_items']} tracked items, "
            f"{counts['reminders']} reminders, "
            f"{counts['log_entries']:>5} log entries, "
            f"{counts['measurements']} measurements, "
            f"{counts['lab_reports']} lab reports"
        )
    print(f"Total runtime: {elapsed:.1f}s")

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed three realistic demo users into a development database."
    )
    parser.add_argument("--only", choices=["priya", "rajesh", "anjali"],
                        help="Seed only one user")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be seeded without writing anything")
    args = parser.parse_args()

    try:
        asyncio.run(seed_all(only=args.only, dry_run=args.dry_run))
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
