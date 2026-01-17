"""Add receipt category tracking columns

Revision ID: 20251027_add_receipt_categories
Revises: 20251010_merge_events_support_with_usage
Create Date: 2025-10-27
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251027_add_receipt_categories'
down_revision = '20251010_merge_events_support_with_usage'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('receipts', sa.Column('categories', sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")))
    op.add_column('receipts', sa.Column('suggested_categories', sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")))
    op.add_column('receipts', sa.Column('categories_locked', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('receipts', sa.Column('categories_updated_at', sa.DateTime(), nullable=True))

    # Drop server defaults after backfilling existing rows to avoid unexpected values on insert.
    op.alter_column('receipts', 'categories', server_default=None)
    op.alter_column('receipts', 'suggested_categories', server_default=None)
    op.alter_column('receipts', 'categories_locked', server_default=None)


def downgrade() -> None:
    op.drop_column('receipts', 'categories_updated_at')
    op.drop_column('receipts', 'categories_locked')
    op.drop_column('receipts', 'suggested_categories')
    op.drop_column('receipts', 'categories')
