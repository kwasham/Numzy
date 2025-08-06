"""add_task_tracking_fields

Revision ID: 28d154d8f89c
Revises: 5b458752c57e
Create Date: 2025-08-04 04:19:11.637808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28d154d8f89c'
down_revision: Union[str, Sequence[str], None] = '5b458752c57e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add task tracking columns
    op.add_column('receipts', sa.Column('task_id', sa.String(), nullable=True))
    op.add_column('receipts', sa.Column('task_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('receipts', sa.Column('task_completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('receipts', sa.Column('task_error', sa.Text(), nullable=True))
    op.add_column('receipts', sa.Column('task_retry_count', sa.Integer(), nullable=True, default=0))
    op.add_column('receipts', sa.Column('processing_duration_ms', sa.Integer(), nullable=True))
    op.add_column('receipts', sa.Column('extraction_progress', sa.Integer(), nullable=True, default=0))
    op.add_column('receipts', sa.Column('audit_progress', sa.Integer(), nullable=True, default=0))
    
    # Add index for task_id
    op.create_index('ix_receipts_task_id', 'receipts', ['task_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_receipts_task_id', 'receipts')
    op.drop_column('receipts', 'audit_progress')
    op.drop_column('receipts', 'extraction_progress')
    op.drop_column('receipts', 'processing_duration_ms')
    op.drop_column('receipts', 'task_retry_count')
    op.drop_column('receipts', 'task_error')
    op.drop_column('receipts', 'task_completed_at')
    op.drop_column('receipts', 'task_started_at')
    op.drop_column('receipts', 'task_id')
