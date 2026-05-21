import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Consultation(Base):
    __tablename__ = "kc_consultations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    patient_name: Mapped[str] = mapped_column(Text, nullable=False)
    patient_phone: Mapped[str] = mapped_column(Text, nullable=False)
    patient_email: Mapped[str | None] = mapped_column(Text)
    condition_category: Mapped[str | None] = mapped_column(Text)
    preferred_slot: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    # 'requested' | 'scheduled' | 'completed' | 'cancelled' | 'no_show'
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'requested'"))
    meeting_link: Mapped[str | None] = mapped_column(Text)
    meeting_provider: Mapped[str | None] = mapped_column(Text)  # 'zoom' | 'meet' | null
    scheduled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    fee_paid_paise: Mapped[int | None] = mapped_column(Integer)
    razorpay_payment_id: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'web'"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=func.now()
    )

    __table_args__ = (
        Index("idx_kc_consult_status", "status", "preferred_slot"),
        Index("idx_kc_consult_user", "user_id"),
        Index("idx_kc_consult_phone", "patient_phone"),
    )

    def __repr__(self) -> str:
        return (
            f"<Consultation id={self.id} patient={self.patient_name!r} status={self.status!r}>"
        )
