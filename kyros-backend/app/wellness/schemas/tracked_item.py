from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator

if TYPE_CHECKING:
    from app.wellness.schemas.reminder import ReminderRead

Category = Literal["medication", "water", "meal", "workout", "vital_check", "custom"]
Source = Literal["manual", "kyros", "ai_extracted"]
Status = Literal["active", "paused", "discontinued"]


# ── per-category metadata shapes ─────────────────────────────────────────────


class MedicationMeta(BaseModel):
    drug_name: str
    dosage: str
    form: Literal["tablet", "capsule", "syrup", "injection", "other"]
    with_food: bool = False
    instructions: str | None = None


class WaterMeta(BaseModel):
    daily_target_ml: int
    glass_size_ml: int = 250


class WorkoutMeta(BaseModel):
    workout_type: str
    duration_minutes: int
    location: str | None = None


class MealMeta(BaseModel):
    meal_name: str
    notes: str | None = None


class CustomMeta(BaseModel):
    title: str
    notes: str | None = None


# ── discriminated-union create request ───────────────────────────────────────
# Each variant validates metadata against its per-category shape.
# The `category` field is the discriminator — FastAPI returns 422 with
# field-level errors when metadata doesn't match the category.


class _ItemCreateBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=500)]
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def _end_after_start(self) -> "_ItemCreateBase":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class MedicationItemCreate(_ItemCreateBase):
    category: Literal["medication"]
    metadata: MedicationMeta


class WaterItemCreate(_ItemCreateBase):
    category: Literal["water"]
    metadata: WaterMeta


class MealItemCreate(_ItemCreateBase):
    category: Literal["meal"]
    metadata: MealMeta


class WorkoutItemCreate(_ItemCreateBase):
    category: Literal["workout"]
    metadata: WorkoutMeta


class VitalCheckItemCreate(_ItemCreateBase):
    category: Literal["vital_check"]
    metadata: dict[str, Any] = {}


class CustomItemCreate(_ItemCreateBase):
    category: Literal["custom"]
    metadata: CustomMeta


TrackedItemCreateRequest = Annotated[
    MedicationItemCreate
    | WaterItemCreate
    | MealItemCreate
    | WorkoutItemCreate
    | VitalCheckItemCreate
    | CustomItemCreate,
    Field(discriminator="category"),
]


# ── generic schemas (for listing / update / ORM read) ────────────────────────


class TrackedItemBase(BaseModel):
    category: Category
    name: str
    item_metadata: dict[str, Any] = Field(
        validation_alias=AliasChoices("item_metadata", "metadata"),
        serialization_alias="metadata",
        default_factory=dict,
    )

    model_config = {"populate_by_name": True}


class TrackedItemCreate(BaseModel):
    """Simple create used internally (not by the route — route uses TrackedItemCreateRequest)."""

    category: Category
    name: str
    item_metadata: dict[str, Any] = Field(
        validation_alias=AliasChoices("item_metadata", "metadata"),
        serialization_alias="metadata",
        default_factory=dict,
    )
    start_date: date
    end_date: date | None = None

    model_config = {"populate_by_name": True}


class TrackedItemUpdate(BaseModel):
    name: str | None = None
    item_metadata: dict[str, Any] | None = Field(
        None,
        validation_alias=AliasChoices("item_metadata", "metadata"),
        serialization_alias="metadata",
    )
    status: Status | None = None
    end_date: date | None = None

    model_config = {"populate_by_name": True}


class TrackedItemRead(TrackedItemBase):
    model_config = {"from_attributes": True, "populate_by_name": True}

    id: uuid.UUID
    user_id: uuid.UUID
    status: Status
    start_date: date
    end_date: date | None
    source: Source
    source_ref: str | None
    created_at: datetime
    updated_at: datetime
    reminders: list[ReminderRead] = []
