"""add billing address fields to users

Revision ID: 20250821_addr_fields
Revises: 20250729_add_clerk_id_safe
Create Date: 2025-08-21
"""
from alembic import op
import sqlalchemy as sa

revision = '20250821_addr_fields'
down_revision = '20250729_add_clerk_id_safe'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('billing_address_line1', sa.String(), nullable=True))
    op.add_column('users', sa.Column('billing_address_line2', sa.String(), nullable=True))
    op.add_column('users', sa.Column('billing_address_city', sa.String(), nullable=True))
    op.add_column('users', sa.Column('billing_address_state', sa.String(), nullable=True))
    op.add_column('users', sa.Column('billing_address_postal_code', sa.String(), nullable=True))
    op.add_column('users', sa.Column('billing_address_country', sa.String(), nullable=True))


def downgrade():
    op.drop_column('users', 'billing_address_country')
    op.drop_column('users', 'billing_address_postal_code')
    op.drop_column('users', 'billing_address_state')
    op.drop_column('users', 'billing_address_city')
    op.drop_column('users', 'billing_address_line2')
    op.drop_column('users', 'billing_address_line1')
