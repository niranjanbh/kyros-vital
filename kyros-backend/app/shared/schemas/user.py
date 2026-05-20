import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    device_id: str | None
    email: str | None
    kyros_patient_id: str | None
    subscription_tier: str
    timezone: str
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    timezone: str | None = None
