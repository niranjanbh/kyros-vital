from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, field_validator


class ParsedTest(BaseModel):
    name: str
    value: str  # str so "Negative", "3.4", etc. all work
    unit: str
    ref_low: float | None = None
    ref_high: float | None = None
    flag: Literal["normal", "low", "high", "critical"]


class LabReportRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID
    report_date: date
    lab_name: str | None
    file_url: str | None
    file_mime: str | None
    parsed: list[ParsedTest]
    source: str
    source_ref: str | None
    note: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    signed_url: str | None = None  # computed in route, never stored

    @field_validator("parsed", mode="before")
    @classmethod
    def _coerce_parsed(cls, v: Any) -> list[Any]:
        # Legacy rows may have {} (empty dict) as the default; coerce to empty list.
        if isinstance(v, dict):
            return []
        return v  # type: ignore[return-value]


class LabReportCreate(BaseModel):
    report_date: date
    lab_name: str | None = None
    parsed: list[ParsedTest] = []
    note: str | None = None


class LabReportUpdate(BaseModel):
    report_date: date | None = None
    lab_name: str | None = None
    parsed: list[ParsedTest] | None = None
    note: str | None = None
