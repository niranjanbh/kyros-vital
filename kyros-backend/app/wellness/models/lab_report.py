import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import TIMESTAMP, Date, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LabReport(Base):
    __tablename__ = "wn_lab_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    lab_name: Mapped[str | None] = mapped_column(Text)
    file_url: Mapped[str | None] = mapped_column(Text)
    file_mime: Mapped[str | None] = mapped_column(Text)
    parsed: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'manual'"))
    source_ref: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=func.now()
    )

    __table_args__ = (Index("idx_wn_lab_reports_user_date", "user_id", "report_date"),)

    def __repr__(self) -> str:
        return (
            f"<LabReport id={self.id} report_date={self.report_date} "
            f"lab_name={self.lab_name!r} status={self.status!r}>"
        )
