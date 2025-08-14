"""add_failed_status_to_enum

Revision ID: c09f83731bf2
Revises: 28d154d8f89c
Create Date: 2025-08-04 05:27:24.066610

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c09f83731bf2'
down_revision: Union[str, Sequence[str], None] = '28d154d8f89c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add FAILED to the receiptstatus enum
    op.execute("ALTER TYPE receiptstatus ADD VALUE 'failed'")


def downgrade() -> None:
    """Downgrade schema."""
    # Note: PostgreSQL doesn't support removing enum values
    pass
