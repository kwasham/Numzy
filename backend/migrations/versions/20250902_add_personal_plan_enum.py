"""Add PERSONAL to plantype enum

Revision ID: 20250902_add_personal_plan
Revises: 20250828_unify_receipts_index_merge
Create Date: 2025-09-02
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20250902_add_personal_plan'
down_revision = '20250828_unify_receipts_index_merge'
branch_labels = None
depends_on = None

def upgrade():
    # Add new enum value PERSONAL if not present. PostgreSQL supports IF NOT EXISTS for ADD VALUE on modern versions.
    # This is irreversible (cannot easily remove enum value), so downgrade is a no-op.
    op.execute("ALTER TYPE plantype ADD VALUE IF NOT EXISTS 'PERSONAL'")


def downgrade():  # pragma: no cover
    # Cannot remove enum value safely; documented no-op.
    pass
