"""add personal plan enum value

Revision ID: 20250821_add_personal
Revises: 28d154d8f89c_add_task_tracking_fields
Create Date: 2025-08-21
"""
from typing import Sequence, Union
from alembic import op

revision: str = "20250821_add_personal"
down_revision: Union[str, None] = "28d154d8f89c_add_task_tracking_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "postgresql":
        op.execute("ALTER TYPE plantype ADD VALUE IF NOT EXISTS 'personal'")


def downgrade() -> None:
    # No downgrade (removing enum values is destructive / complex)
    pass
