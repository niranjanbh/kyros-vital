import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import TIMESTAMP, Date, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.wellness.models.reminder import Reminder


class TrackedItem(Base):
    __tablename__ = "wn_tracked_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # "metadata" is reserved on DeclarativeBase; map to Python attr item_metadata
    item_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'manual'"))
    source_ref: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=func.now()
    )

    reminders: Mapped[list["Reminder"]] = relationship(
        "Reminder", back_populates="tracked_item", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_wn_items_user_status", "user_id", "status"),
        Index("idx_wn_items_category", "user_id", "category"),
    )

    def __repr__(self) -> str:
        return (
            f"<TrackedItem id={self.id} category={self.category!r} name={self.name!r} "
            f"status={self.status!r}>"
        )
