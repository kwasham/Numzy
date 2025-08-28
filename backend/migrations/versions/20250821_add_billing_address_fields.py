"""(Deprecated duplicate) billing address migration retained as no-op.

This file originally added billing address columns but a parallel
variant `20250821_addr_fields` was merged downstream. To avoid a
permanent secondary head, we convert this migration into a no-op
depending on the same parent so Alembic can linearize or it can be
deleted after all environments are stamped.

Revision ID: 20250821_add_billing_address_fields
Revises: 20250729_add_clerk_id_safe
Create Date: 2025-08-21
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250821_add_billing_address_fields'
down_revision = '20250729_add_clerk_id_safe'
branch_labels = None
depends_on = None

def upgrade():
    # No-op: superseded by 20250821_addr_fields + downstream merge.
    pass


def downgrade():
    # No-op (original columns intentionally retained)
    pass
