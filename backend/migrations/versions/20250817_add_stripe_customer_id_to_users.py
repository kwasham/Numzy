"""add stripe_customer_id to users

Revision ID: e7f8a9b0c1d2
Revises: 20250809_add_receipt_indexes, cadb996be101
Create Date: 2025-08-17 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = ('20250809_add_receipt_indexes', 'cadb996be101')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema by adding stripe_customer_id to users.
    The column is nullable to allow backfill, with a unique constraint for mapping.
    """
    op.add_column('users', sa.Column('stripe_customer_id', sa.String(), nullable=True))
    op.create_unique_constraint('uq_users_stripe_customer_id', 'users', ['stripe_customer_id'])


def downgrade() -> None:
    """Revert schema changes."""
    op.drop_constraint('uq_users_stripe_customer_id', 'users', type_='unique')
    op.drop_column('users', 'stripe_customer_id')
