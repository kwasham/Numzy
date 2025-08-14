"""Add background_jobs table

Revision ID: add_background_jobs
Revises: 
Create Date: 2025-08-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_background_jobs'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('background_jobs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), default=0),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('receipt_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['receipt_id'], ['receipts.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_background_jobs_status'), 'background_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_background_jobs_user_id'), 'background_jobs', ['user_id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_background_jobs_user_id'), table_name='background_jobs')
    op.drop_index(op.f('ix_background_jobs_status'), table_name='background_jobs')
    op.drop_table('background_jobs')