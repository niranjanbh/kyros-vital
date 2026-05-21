"""add consultations table and users.role column

Revision ID: b5c9a72f3d1e
Revises: 4183f546841c
Create Date: 2026-05-21 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5c9a72f3d1e"
down_revision: Union[str, None] = "4183f546841c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add role column to users with a check constraint — TEXT not ENUM for future flexibility
    op.add_column(
        "users",
        sa.Column("role", sa.Text(), nullable=False, server_default=sa.text("'user'")),
    )
    op.create_check_constraint("ck_users_role", "users", "role IN ('user', 'superadmin')")

    # kc_consultations: booking/consultation records for the clinic domain
    op.create_table(
        "kc_consultations",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("patient_name", sa.Text(), nullable=False),
        sa.Column("patient_phone", sa.Text(), nullable=False),
        sa.Column("patient_email", sa.Text(), nullable=True),
        sa.Column("condition_category", sa.Text(), nullable=True),
        sa.Column("preferred_slot", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'requested'"),
        ),
        sa.Column("meeting_link", sa.Text(), nullable=True),
        sa.Column("meeting_provider", sa.Text(), nullable=True),
        sa.Column("scheduled_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("fee_paid_paise", sa.Integer(), nullable=True),
        sa.Column("razorpay_payment_id", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default=sa.text("'web'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_kc_consult_status", "kc_consultations", ["status", "preferred_slot"])
    op.create_index("idx_kc_consult_user", "kc_consultations", ["user_id"])
    op.create_index("idx_kc_consult_phone", "kc_consultations", ["patient_phone"])


def downgrade() -> None:
    op.drop_index("idx_kc_consult_phone", table_name="kc_consultations")
    op.drop_index("idx_kc_consult_user", table_name="kc_consultations")
    op.drop_index("idx_kc_consult_status", table_name="kc_consultations")
    op.drop_table("kc_consultations")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.drop_column("users", "role")
