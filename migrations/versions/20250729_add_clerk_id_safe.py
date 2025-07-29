"""safely add clerk_id to users table


Revision ID: 20250729_add_clerk_id_safe
Revises: 25ca9dbfe70d


Create Date: 2025-07-29
"""
down_revision = '25ca9dbfe70d'
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision = '20250729_add_clerk_id_safe'
down_revision = '25ca9dbfe70d'
branch_labels = None
depends_on = None

def upgrade():
    # Step 1: Add clerk_id column as nullable
    op.add_column('users', sa.Column('clerk_id', sa.String(), nullable=True))
    # Step 2: Populate clerk_id for existing users with UUIDs
    conn = op.get_bind()
    users = conn.execute(sa.text('SELECT id FROM users')).fetchall()
    for user in users:
        conn.execute(sa.text('UPDATE users SET clerk_id = :cid WHERE id = :id'), {'cid': str(uuid.uuid4()), 'id': user.id})
    # Step 3: Alter column to non-nullable
    op.alter_column('users', 'clerk_id', nullable=False)
    # Step 4: Add unique constraint
    op.create_unique_constraint('uq_users_clerk_id', 'users', ['clerk_id'])

def downgrade():
    op.drop_constraint('uq_users_clerk_id', 'users', type_='unique')
    op.drop_column('users', 'clerk_id')
