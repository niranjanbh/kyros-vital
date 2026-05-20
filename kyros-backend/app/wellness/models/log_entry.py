import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LogEntry(Base):
    __tablename__ = "wn_log_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tracked_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wn_tracked_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    reminder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("wn_reminders.id", ondelete="SET NULL"),
        nullable=True,
    )
    fire_key: Mapped[str | None] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    note: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'manual'"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )

    __table_args__ = (
        Index(
            "uniq_wn_log_fire_key",
            "fire_key",
            unique=True,
            postgresql_where=text("fire_key IS NOT NULL"),
        ),
        Index("idx_wn_log_user_time", "user_id", "occurred_at"),
    )

    def __repr__(self) -> str:
        return f"<LogEntry id={self.id} action={self.action!r} fire_key={self.fire_key!r}>"
