"""add_failed_status_to_receiptstatus_enum

Revision ID: 0d2b0ca44faa
Revises: 28d154d8f89c
Create Date: 2025-08-04

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0d2b0ca44faa'
down_revision = '28d154d8f89c'
branch_labels = None
depends_on = None


def upgrade():
    # Add 'failed' to the receiptstatus enum type
    op.execute("ALTER TYPE receiptstatus ADD VALUE IF NOT EXISTS 'failed'")


def downgrade():
    # Note: PostgreSQL doesn't support removing enum values
    # This is a one-way migration
    pass
