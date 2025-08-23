"""Merge heads and add subscription state fields

Revision ID: 20250823_merge_and_sub_state
Revises: e7f8a9b0c1d2, 20250821_addr_fields
Create Date: 2025-08-23
"""
from alembic import op
import sqlalchemy as sa

revision = '20250823_merge_and_sub_state'
down_revision = ('e7f8a9b0c1d2', '20250821_addr_fields')
branch_labels = None
depends_on = None

def upgrade():
    # Add subscription/payment tracking fields if they don't already exist
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('subscription_status', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('last_invoice_status', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('payment_state', sa.String(), nullable=True))
    op.create_index('ix_users_subscription_status', 'users', ['subscription_status'])
    op.create_index('ix_users_payment_state', 'users', ['payment_state'])


def downgrade():
    op.drop_index('ix_users_payment_state', table_name='users')
    op.drop_index('ix_users_subscription_status', table_name='users')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('payment_state')
        batch_op.drop_column('last_invoice_status')
        batch_op.drop_column('subscription_status')
