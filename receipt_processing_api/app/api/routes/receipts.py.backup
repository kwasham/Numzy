
"""API routes for receipt upload and retrieval."""

from __future__ import annotations

import asyncio
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_user, get_clerk_user
from app.core.security import get_current_user
from app.models.schemas import ReceiptRead, ReceiptUpdate
from app.models.tables import Receipt, ReceiptStatus, User
from app.services.storage_service import StorageService
from app.services.extraction_service import ExtractionService
from app.services.audit_service import AuditService
from app.services.billing_service import BillingService


router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post("", response_model=ReceiptRead, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_clerk_user),
) -> ReceiptRead:
    """Upload a new receipt image.

    Stores the file, creates a database record and schedules
    extraction and audit tasks. Returns the receipt metadata with
    status set to pending.
    """
    # Enforce monthly quota via the billing service
    billing = BillingService()
    # In a real implementation we would record usage and check quotas
    # Here we simply proceed
    storage = StorageService()
    relative_path, original_filename = await storage.save_upload(file, user.id)
    receipt = Receipt(
        owner_id=user.id,
        organisation_id=None,
        file_path=relative_path,
        filename=original_filename,
        status=ReceiptStatus.PENDING,
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)

    async def process_receipt_task(receipt_id: int, user_id: int) -> None:
        """Background task to run extraction and audit services."""
        # Use a new session inside the background task
        async for session in get_db_session():
            # Load the receipt again to avoid stale instance errors
            rec = await session.get(Receipt, receipt_id)
            if not rec:
                return
            rec.status = ReceiptStatus.PROCESSING
            await session.commit()
            # Load file data
            storage_inner = StorageService()
            file_bytes = storage_inner.get_full_path(rec.file_path).read_bytes()
            extraction_service = ExtractionService()
            details = await extraction_service.extract(file_bytes, rec.filename)
            # Run audit
            audit_service = AuditService(session)
            # Determine if the user has created a natural-language rule
            # For illustration, suppose you store the NL description on the receipt record
            nl_description = rec.nl_rule_description  # or fetch from another table
            threshold = rec.amount_limit or 50.0

            if nl_description:
                decision = await audit_service.audit(
                    details,
                    user_id,
                    nl_rule_description=nl_description,
                    amount_limit=threshold,
                )
            else:
                decision = await audit_service.audit(details, user_id)
                # Update receipt record
                rec.extracted_data = details.model_dump()
                rec.audit_decision = decision.model_dump()
                rec.status = ReceiptStatus.COMPLETED
                await session.commit()
                return

    # Schedule the background task
    background_tasks.add_task(process_receipt_task, receipt.id, user.id)
    return ReceiptRead.from_orm(receipt)


@router.get("", response_model=List[ReceiptRead])
async def list_receipts(
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> List[ReceiptRead]:
    """List all receipts for the current user."""
    query = Receipt.__table__.select().where(Receipt.owner_id == user.id)
    result = await db.execute(query)
    rows = result.fetchall()
    return [ReceiptRead.from_orm(Receipt(**row._mapping)) for row in rows]


@router.get("/{receipt_id}", response_model=ReceiptRead)
async def get_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> ReceiptRead:
    """Retrieve a specific receipt by ID."""
    receipt = await db.get(Receipt, receipt_id)
    if not receipt or receipt.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return ReceiptRead.from_orm(receipt)


@router.get("/{receipt_id}/audit", response_model=ReceiptRead)
async def get_receipt_audit(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> ReceiptRead:
    """Return the audit decision for a receipt."""
    receipt = await db.get(Receipt, receipt_id)
    if not receipt or receipt.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if receipt.status != ReceiptStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Receipt not yet processed")
    return ReceiptRead.from_orm(receipt)



# --- CRUD update and delete endpoints ---

@router.put("/{receipt_id}", response_model=ReceiptRead)
async def update_receipt(
    receipt_id: int,
    update: ReceiptUpdate,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> ReceiptRead:
    """Update a receipt (filename, status, extracted_data, audit_decision)."""
    receipt = await db.get(Receipt, receipt_id)
    if not receipt or receipt.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Receipt not found")
    update_data = update.dict(exclude_unset=True)
    from datetime import datetime, timezone
    for field, value in update_data.items():
        if value is not None:
            if field == "updated_at" and isinstance(value, datetime) and value.tzinfo is not None:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            setattr(receipt, field, value)
    await db.commit()
    await db.refresh(receipt)
    return ReceiptRead.from_orm(receipt)

@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_clerk_user),
):
    """Delete a receipt by ID."""
    receipt = await db.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    # Get owner's clerk_id
    owner = await db.get(User, receipt.owner_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    from app.api.dependencies import require_owner_or_admin
    require_owner_or_admin(user, owner.clerk_id)
    await db.delete(receipt)
    await db.commit()
    return None