"""add error_log table

Revision ID: f6a1b2c3d4e5
Revises: e5f0a3b6c9d2
Create Date: 2026-05-21

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f6a1b2c3d4e5"
down_revision = "e5f0a3b6c9d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "error_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("error_type", sa.String(200), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("traceback", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=True),
        sa.Column("query_params", sa.String(1000), nullable=True),
        sa.Column("request_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_error_log_occurred_at", "error_log", ["occurred_at"], unique=False)
    op.create_index("ix_error_log_status_code", "error_log", ["status_code"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_error_log_status_code", table_name="error_log")
    op.drop_index("ix_error_log_occurred_at", table_name="error_log")
    op.drop_table("error_log")
