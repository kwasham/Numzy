"""add composite index on receipts(owner_id, created_at desc)

Revision ID: add_receipts_owner_created_at_idx
Revises: 
Create Date: 2025-08-28
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_receipts_owner_created_at_idx'
# Align with latest alembic head (20250823_add_subscription_state_fields.py)
down_revision = 'add_subscription_state_fields'
branch_labels = None
depends_on = None

INDEX_NAME = 'ix_receipts_owner_created_at'


def upgrade() -> None:
    # Use IF NOT EXISTS pattern via try/except (Alembic doesn't have portable IF NOT EXISTS)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {idx['name'] for idx in inspector.get_indexes('receipts')}
    if INDEX_NAME not in existing:
        op.execute(sa.text(f'CREATE INDEX {INDEX_NAME} ON receipts (owner_id, created_at DESC)'))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {idx['name'] for idx in inspector.get_indexes('receipts')}
    if INDEX_NAME in existing:
        op.execute(sa.text(f'DROP INDEX {INDEX_NAME}'))
