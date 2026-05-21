"""add users.is_active column

Revision ID: c3d8e1f4a9b2
Revises: b5c9a72f3d1e
Create Date: 2026-05-21 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d8e1f4a9b2"
down_revision: Union[str, None] = "b5c9a72f3d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_active")
