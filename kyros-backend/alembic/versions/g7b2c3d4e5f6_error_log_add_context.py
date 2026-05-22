"""error_log: add user_agent, endpoint, response_summary columns

Revision ID: g7b2c3d4e5f6
Revises: f6a1b2c3d4e5
Create Date: 2026-05-22 09:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g7b2c3d4e5f6"
down_revision: Union[str, None] = "f6a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("error_log", sa.Column("user_agent", sa.Text(), nullable=True))
    op.add_column("error_log", sa.Column("endpoint", sa.String(200), nullable=True))
    # Short JSON summary of the error response returned to the client (code + message)
    op.add_column("error_log", sa.Column("response_summary", sa.Text(), nullable=True))
    op.create_index("ix_error_log_endpoint", "error_log", ["endpoint"])


def downgrade() -> None:
    op.drop_index("ix_error_log_endpoint", table_name="error_log")
    op.drop_column("error_log", "response_summary")
    op.drop_column("error_log", "endpoint")
    op.drop_column("error_log", "user_agent")
