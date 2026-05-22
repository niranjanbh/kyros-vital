from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.wellness.schemas.schedule import Schedule


class ReminderRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tracked_item_id: uuid.UUID
    schedule: Schedule
    message_template: str
    channels: list[str]
    snooze_minutes: int
    taken_window_minutes: int | None
    active: bool
    created_at: datetime
    updated_at: datetime


class ReminderCreate(BaseModel):
    schedule: Schedule
    message_template: str
    channels: list[str] = Field(default_factory=lambda: ["in_app"])
    snooze_minutes: int = Field(default=15, ge=1, le=240)
    taken_window_minutes: int | None = Field(default=None, ge=5, le=480)


class ReminderUpdate(BaseModel):
    schedule: Schedule | None = None
    message_template: str | None = None
    channels: list[str] | None = None
    snooze_minutes: int | None = Field(default=None, ge=1, le=240)
    taken_window_minutes: int | None = Field(default=None, ge=5, le=480)
    active: bool | None = None


class UpcomingFire(BaseModel):
    reminder_id: uuid.UUID
    tracked_item_id: uuid.UUID
    fire_at: datetime
    fire_key: str
    payload: dict[str, Any]
    snooze_minutes: int
    taken_window_minutes: int | None
