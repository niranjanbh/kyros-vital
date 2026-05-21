"""add users.name column

Revision ID: d4e9f2a5b8c1
Revises: c3d8e1f4a9b2
Create Date: 2026-05-21 13:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e9f2a5b8c1"
down_revision: Union[str, None] = "c3d8e1f4a9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "name")
