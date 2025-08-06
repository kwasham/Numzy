"""API routes for receipt upload and retrieval."""

from __future__ import annotations

import os
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.api.dependencies import get_clerk_user, get_db_session, get_user
from app.models.enums import ReceiptStatus
from app.models.schemas import ReceiptRead, ReceiptUpdate
from app.models.tables import Receipt, BackgroundJob, User
from app.services.billing_service import BillingService
from app.services.storage_service import StorageService
from app.core.tasks import extract_and_audit_receipt

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post("", response_model=ReceiptRead)
async def upload_receipt(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> ReceiptRead:
    """Upload a new receipt for processing."""
    # Check file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Check file size (10MB limit)
    file_size = 0
    contents = await file.read()
    file_size = len(contents)
    if file_size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB")
    
    # Reset file position after reading
    file.file.seek(0)
    
    # Save file to storage
    storage = StorageService()
    file_path, original_filename = await storage.save_upload(file, user.id)
    
    # Create receipt record
    receipt = Receipt(
        owner_id=user.id,
        file_path=file_path,
        filename=original_filename,
        status=ReceiptStatus.PENDING,
    )
    
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    
    # Queue background task for processing with user_id
    task_message = extract_and_audit_receipt.send(receipt.id, user.id)
    
    # Update receipt with task ID
    receipt.task_id = task_message.message_id
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    
    return ReceiptRead.from_orm(receipt)


@router.get("", response_model=List[ReceiptRead])
async def list_receipts(
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> List[ReceiptRead]:
    """List all receipts for the current user."""
    query = select(Receipt).where(Receipt.owner_id == user.id)
    result = await db.execute(query)
    receipts = result.scalars().all()
    return receipts


@router.get("/{receipt_id}", response_model=ReceiptRead)
async def get_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> ReceiptRead:
    """Get a specific receipt by ID."""
    query = select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id)
    result = await db.execute(query)
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return receipt


@router.patch("/{receipt_id}", response_model=ReceiptRead)
async def update_receipt(
    receipt_id: int,
    update_data: ReceiptUpdate,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> ReceiptRead:
    """Update a receipt's extracted data or audit decision."""
    query = select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id)
    result = await db.execute(query)
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    # Apply updates
    update_dict = update_data.dict(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(receipt, field, value)
    
    await db.commit()
    await db.refresh(receipt)
    return receipt


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
):  # Remove the return type annotation
    """Delete a receipt."""
    query = select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id)
    result = await db.execute(query)
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    await db.delete(receipt)
    await db.commit()
    # Don't return anything for 204 status


# For the audit endpoint, create a simple response model inline

class AuditResponse(BaseModel):
    """Audit decision response."""
    receipt_id: int
    decision: Dict[str, Any]
    created_at: datetime


@router.get("/{receipt_id}/audit", response_model=AuditResponse)
async def get_audit_decision(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> AuditResponse:
    """Get the audit decision for a receipt."""
    query = select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id)
    result = await db.execute(query)
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    if not receipt.audit_decision:
        raise HTTPException(status_code=404, detail="No audit decision available yet")
    
    return AuditResponse(
        receipt_id=receipt.id,
        decision=receipt.audit_decision,
        created_at=receipt.updated_at or receipt.created_at
    )

