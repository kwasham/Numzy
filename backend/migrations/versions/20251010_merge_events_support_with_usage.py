"""merge events/support tables branch with trial/usage branch

Revision ID: 20251010_merge_events_support_with_usage
Revises: 20251010_add_events_support, add_trial_usage_fields_20250902
Create Date: 2025-10-10
"""
from __future__ import annotations

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision = '20251010_merge_events_support_with_usage'
down_revision = ('20251010_add_events_support', 'add_trial_usage_fields_20250902')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No-op merge: schema already applied by parent heads.
    pass


def downgrade() -> None:
    # No-op merge.
    pass
