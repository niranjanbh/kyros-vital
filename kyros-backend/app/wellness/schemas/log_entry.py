from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

LogAction = Literal["taken", "skipped", "snoozed", "logged_value", "acknowledged"]


class LogEntryRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    tracked_item_id: uuid.UUID
    reminder_id: uuid.UUID | None
    fire_key: str | None
    action: LogAction
    value: dict[str, Any]
    note: str | None
    occurred_at: datetime
    source: str
    created_at: datetime


class LogEntryCreate(BaseModel):
    tracked_item_id: uuid.UUID
    action: LogAction
    occurred_at: datetime
    reminder_id: uuid.UUID | None = None
    fire_key: str | None = None
    value: dict[str, Any] = Field(default_factory=dict)
    note: str | None = None
    snooze_minutes: int | None = None
