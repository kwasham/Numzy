"""add events and support tables

Revision ID: 20251010_add_events_support
Revises: 
Create Date: 2025-10-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251010_add_events_support'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if not insp.has_table('events'):
        op.create_table(
            'events',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('type', sa.String(), nullable=True),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('meta', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )

    if not insp.has_table('support_threads'):
        op.create_table(
            'support_threads',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('subject', sa.String(), nullable=True),
            sa.Column('author_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )

    if not insp.has_table('support_messages'):
        op.create_table(
            'support_messages',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('thread_id', sa.Integer(), sa.ForeignKey('support_threads.id'), nullable=False),
            sa.Column('author_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )


def downgrade() -> None:
    op.drop_table('support_messages')
    op.drop_table('support_threads')
    op.drop_table('events')
