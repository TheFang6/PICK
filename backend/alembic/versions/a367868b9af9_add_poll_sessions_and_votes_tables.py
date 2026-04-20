"""add_poll_sessions_and_votes_tables

Revision ID: a367868b9af9
Revises: ef50f8b44f33
Create Date: 2026-04-20 09:52:45.768102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a367868b9af9'
down_revision: Union[str, Sequence[str], None] = 'ef50f8b44f33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('poll_sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('chat_id', sa.Text(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=True),
    sa.Column('candidates', sa.JSON(), nullable=False),
    sa.Column('session_id', sa.Text(), nullable=True),
    sa.Column('status', sa.Enum('ACTIVE', 'COMPLETED', 'CANCELLED', name='pollstatus'), nullable=False),
    sa.Column('winner_restaurant_id', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
    sa.ForeignKeyConstraint(['winner_restaurant_id'], ['restaurants.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('poll_votes',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('poll_session_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('restaurant_id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['poll_session_id'], ['poll_sessions.id'], ),
    sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('poll_session_id', 'user_id', name='uq_poll_vote_session_user')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('poll_votes')
    op.drop_table('poll_sessions')
