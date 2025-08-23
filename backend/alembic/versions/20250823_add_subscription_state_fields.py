"""Add subscription state fields to users

Revision ID: add_subscription_state_fields
Revises: add_background_jobs
Create Date: 2025-08-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_subscription_state_fields'
down_revision = 'add_background_jobs'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('subscription_status', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_invoice_status', sa.String(), nullable=True))
    op.add_column('users', sa.Column('payment_state', sa.String(), nullable=True))
    op.create_index('ix_users_subscription_status', 'users', ['subscription_status'])
    op.create_index('ix_users_payment_state', 'users', ['payment_state'])


def downgrade():
    op.drop_index('ix_users_payment_state', table_name='users')
    op.drop_index('ix_users_subscription_status', table_name='users')
    op.drop_column('users', 'payment_state')
    op.drop_column('users', 'last_invoice_status')
    op.drop_column('users', 'subscription_status')
