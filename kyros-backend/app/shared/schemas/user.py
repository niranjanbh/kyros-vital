import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    device_id: str | None
    name: str | None
    age: int | None
    gender: str | None
    email: str | None
    kyros_patient_id: str | None
    subscription_tier: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    age: int | None = None
    gender: str | None = None
    email: EmailStr | None = None
    timezone: str | None = None
    # subscription_tier is admin-only — the route rejects it with 403
    subscription_tier: str | None = None
