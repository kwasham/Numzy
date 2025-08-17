"""Add FAILED to receiptstatus enum (placeholder)

Revision ID: 8f0b1a2c3d4e
Revises: 78dce29a5da6
Create Date: 2025-08-04 05:40:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f0b1a2c3d4e'
down_revision: Union[str, Sequence[str], None] = '78dce29a5da6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Upgrade schema (no-op placeholder)."""
	pass


def downgrade() -> None:
	"""Downgrade schema (no-op placeholder)."""
	pass
