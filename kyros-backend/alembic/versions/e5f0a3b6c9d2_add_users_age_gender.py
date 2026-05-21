"""add users.age and users.gender columns

Revision ID: e5f0a3b6c9d2
Revises: d4e9f2a5b8c1
Create Date: 2026-05-21 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f0a3b6c9d2"
down_revision: Union[str, None] = "d4e9f2a5b8c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("gender", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_users_gender",
        "users",
        "gender IN ('male', 'female', 'other', 'prefer_not_to_say')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_gender", "users", type_="check")
    op.drop_column("users", "gender")
    op.drop_column("users", "age")
