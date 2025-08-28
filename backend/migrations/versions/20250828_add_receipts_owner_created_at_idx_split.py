"""Add composite index on receipts(owner_id, created_at DESC)

Revision ID: 20250828_add_receipts_owner_created_at_idx_split
Revises: 20250823_merge_and_sub_state
Create Date: 2025-08-28
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20250828_add_receipts_owner_created_at_idx_split"
down_revision = "20250823_merge_and_sub_state"
branch_labels = None
depends_on = None

INDEX_NAME = "ix_receipts_owner_created_at"

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {idx["name"] for idx in inspector.get_indexes("receipts")}
    if INDEX_NAME not in existing:
        op.execute(sa.text(f"CREATE INDEX {INDEX_NAME} ON receipts (owner_id, created_at DESC)"))

def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {idx["name"] for idx in inspector.get_indexes("receipts")}
    if INDEX_NAME in existing:
        op.execute(sa.text(f"DROP INDEX {INDEX_NAME}"))
