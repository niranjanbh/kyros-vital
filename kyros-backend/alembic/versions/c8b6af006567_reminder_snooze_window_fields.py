"""reminder_snooze_window_fields

Revision ID: c8b6af006567
Revises: g7b2c3d4e5f6
Create Date: 2026-05-22 16:08:23.585162

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c8b6af006567'
down_revision: Union[str, None] = 'g7b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('wn_reminders', sa.Column('snooze_minutes', sa.Integer(), server_default=sa.text('15'), nullable=False))
    op.add_column('wn_reminders', sa.Column('taken_window_minutes', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('wn_reminders', 'taken_window_minutes')
    op.drop_column('wn_reminders', 'snooze_minutes')
    # error_log table intentionally omitted — managed by a separate migration
    op.create_table('error_log',
    sa.Column('id', sa.UUID(), autoincrement=False, nullable=False),
    sa.Column('occurred_at', postgresql.TIMESTAMP(timezone=True), autoincrement=False, nullable=False),
    sa.Column('method', sa.VARCHAR(length=10), autoincrement=False, nullable=False),
    sa.Column('path', sa.VARCHAR(length=500), autoincrement=False, nullable=False),
    sa.Column('status_code', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('error_type', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('error_detail', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('traceback', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('user_id', sa.UUID(), autoincrement=False, nullable=True),
    sa.Column('request_id', sa.VARCHAR(length=64), autoincrement=False, nullable=True),
    sa.Column('ip_address', sa.VARCHAR(length=45), autoincrement=False, nullable=True),
    sa.Column('duration_ms', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True),
    sa.Column('query_params', sa.VARCHAR(length=1000), autoincrement=False, nullable=True),
    sa.Column('request_body', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('user_agent', sa.TEXT(), autoincrement=False, nullable=True),
    sa.Column('endpoint', sa.VARCHAR(length=200), autoincrement=False, nullable=True),
    sa.Column('response_summary', sa.TEXT(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('error_log_user_id_fkey'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('error_log_pkey'))
    )
    op.create_index(op.f('ix_error_log_status_code'), 'error_log', ['status_code'], unique=False)
    op.create_index(op.f('ix_error_log_occurred_at'), 'error_log', ['occurred_at'], unique=False)
    op.create_index(op.f('ix_error_log_endpoint'), 'error_log', ['endpoint'], unique=False)
    # ### end Alembic commands ###
