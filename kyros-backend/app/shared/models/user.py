import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Boolean, CheckConstraint, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    device_id: Mapped[str | None] = mapped_column(Text, index=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    kyros_patient_id: Mapped[str | None] = mapped_column(Text)
    subscription_tier: Mapped[str] = mapped_column(Text, server_default=text("'free'"))
    timezone: Mapped[str] = mapped_column(Text, server_default=text("'Asia/Kolkata'"))
    role: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'user'"))
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("role IN ('user', 'superadmin')", name="ck_users_role"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} device_id={self.device_id!r} email={self.email!r}>"
