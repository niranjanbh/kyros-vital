import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import TIMESTAMP, Boolean, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.wellness.models.tracked_item import TrackedItem


class Reminder(Base):
    __tablename__ = "wn_reminders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tracked_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wn_tracked_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    schedule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    message_template: Mapped[str] = mapped_column(Text, nullable=False)
    channels: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default=text("ARRAY['in_app']::text[]")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=func.now()
    )

    tracked_item: Mapped["TrackedItem"] = relationship("TrackedItem", back_populates="reminders")

    __table_args__ = (
        Index("idx_wn_reminders_active", "active", postgresql_where=text("active = true")),
    )

    def __repr__(self) -> str:
        return (
            f"<Reminder id={self.id} tracked_item_id={self.tracked_item_id} "
            f"active={self.active}>"
        )
