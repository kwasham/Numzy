"""merge_failed_status_migrations

Revision ID: 78dce29a5da6
Revises: 0d2b0ca44faa, c09f83731bf2
Create Date: 2025-08-04 05:43:02.314642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78dce29a5da6'
down_revision: Union[str, Sequence[str], None] = ('0d2b0ca44faa', 'c09f83731bf2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
