"""add_user_attendance_table

Revision ID: ef50f8b44f33
Revises: 7b1ab9603757
Create Date: 2026-04-20 09:35:05.836403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ef50f8b44f33'
down_revision: Union[str, Sequence[str], None] = '7b1ab9603757'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('user_attendance',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('date', sa.Date(), nullable=False),
    sa.Column('status', sa.Enum('IN_OFFICE', 'WFH', 'UNKNOWN', name='attendancestatus'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'date', name='uq_user_attendance_user_date')
    )
    op.create_index('ix_user_attendance_date_status', 'user_attendance', ['date', 'status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_user_attendance_date_status', table_name='user_attendance')
    op.drop_table('user_attendance')
