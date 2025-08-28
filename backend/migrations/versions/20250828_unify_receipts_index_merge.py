"""Merge heads (billing address duplicate + receipts index split)

Revision ID: 20250828_unify_receipts_index_merge
Revises: 20250821_add_billing_address_fields, 20250828_add_receipts_owner_created_at_idx_split
Create Date: 2025-08-28
"""
from __future__ import annotations

revision = "20250828_unify_receipts_index_merge"
# Merge the two outstanding heads into a single linear head
# Heads being merged:
# - 20250821_add_billing_address_fields (now a no-op duplicate of addr fields)
# - 20250828_add_receipts_owner_created_at_idx_split (adds composite index)
# This merge allows future migrations to target a single head.
down_revision = ("20250821_add_billing_address_fields", "20250828_add_receipts_owner_created_at_idx_split")
branch_labels = None
depends_on = None

def upgrade():  # no-op merge
    pass

def downgrade():  # cannot unmerge safely
    pass
