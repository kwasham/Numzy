"""add trial and usage tracking fields

Revision ID: add_trial_usage_fields_20250902
Revises: 20250902_add_personal_plan
Create Date: 2025-09-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_trial_usage_fields_20250902'
down_revision = '20250902_add_personal_plan'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('trial_started_at', sa.DateTime(), nullable=True))
        batch.add_column(sa.Column('trial_ends_at', sa.DateTime(), nullable=True))
        batch.add_column(sa.Column('monthly_receipt_count', sa.Integer(), nullable=True, server_default='0'))
        batch.add_column(sa.Column('last_receipt_reset_at', sa.DateTime(), nullable=True))

    # Clear server_default after backfill to keep app-side control
    op.execute("ALTER TABLE users ALTER COLUMN monthly_receipt_count DROP DEFAULT")


def downgrade() -> None:
    with op.batch_alter_table('users') as batch:
        batch.drop_column('trial_started_at')
        batch.drop_column('trial_ends_at')
        batch.drop_column('monthly_receipt_count')
        batch.drop_column('last_receipt_reset_at')
