"""add receipt indexes (no-op placeholder)

Revision ID: 20250809_add_receipt_indexes
Revises: 5979c07c75bd
Create Date: 2025-08-09 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20250809_add_receipt_indexes'
down_revision: Union[str, Sequence[str], None] = '5979c07c75bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Upgrade schema.
	This is a placeholder migration to maintain revision continuity.
	Add concrete indexes here in the future if needed.
	"""
	pass


def downgrade() -> None:
	"""Downgrade schema."""
	pass
