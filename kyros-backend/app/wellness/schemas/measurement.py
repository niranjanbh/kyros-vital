from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel

MeasurementType = Literal[
    "weight",
    "bp_systolic",
    "bp_diastolic",
    "heart_rate",
    "fasting_glucose",
    "hba1c",
    "body_temp",
    "steps",
]


class MeasurementRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    type: MeasurementType
    value: Decimal
    unit: str
    measured_at: datetime
    reference_range: dict[str, Any] | None
    source: str
    source_ref: str | None
    note: str | None
    created_at: datetime


class MeasurementCreate(BaseModel):
    type: MeasurementType
    value: Decimal
    unit: str
    measured_at: datetime
    reference_range: dict[str, Any] | None = None
    note: str | None = None


class MeasurementUpdate(BaseModel):
    type: MeasurementType | None = None
    value: Decimal | None = None
    unit: str | None = None
    measured_at: datetime | None = None
    reference_range: dict[str, Any] | None = None
    note: str | None = None
