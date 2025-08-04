"""empty message

Revision ID: 5b458752c57e
Revises: 20250729_add_clerk_id_safe, 20250729_add_clerk_id
Create Date: 2025-07-29 01:15:44.351478

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b458752c57e'
down_revision: Union[str, Sequence[str], None] = '20250729_add_clerk_id_safe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
