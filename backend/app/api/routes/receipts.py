"""API routes for receipt upload and retrieval."""

from __future__ import annotations

import os
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import hmac
import hashlib
import base64
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy import func
from pydantic import BaseModel

from app.api.dependencies import get_clerk_user, get_db_session, get_user, enforce_rate_limit, enforce_tiered_rate_limit
from app.core.config import settings
from app.models.enums import ReceiptStatus
from app.models.schemas import ReceiptRead, ReceiptUpdate
from app.models.tables import Receipt, BackgroundJob, User
from app.services.billing_service import BillingService
from app.core.observability import sentry_breadcrumb, sentry_set_tags
from app.services.storage_service import StorageService, load_file_from_storage
from app.utils.image_processing import generate_thumbnail
from app.core.tasks import extract_and_audit_receipt
from app.core.tasks import _publish_event  # lightweight publisher

router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.post("", response_model=ReceiptRead)
async def upload_receipt(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
    request: Request = None,
) -> ReceiptRead:
    """Upload a new receipt for processing."""
    # Tier-aware rate limit: per-plan uploads per minute
    await enforce_tiered_rate_limit(user, "upload", cost=1)
    # Monthly quota enforcement (simple count of receipts created this calendar month)
    try:
        billing = BillingService()
        plan = getattr(user, "plan", None)
        from app.models.enums import PlanType as _PT
        if plan is None:
            plan = _PT.FREE
        # Determine month boundaries (UTC)
        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
        # Next month start for exclusive end
        if now.month == 12:
            next_start = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            next_start = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
        q = select(func.count(Receipt.id)).where(Receipt.owner_id == user.id, Receipt.created_at >= month_start, Receipt.created_at < next_start)
        result = await db.execute(q)
        count = result.scalar() or 0
        limit = billing.get_monthly_quota(plan)
        if limit != float("inf") and count >= limit:
            try:
                sentry_breadcrumb(
                    category="quota",
                    message="upload_receipt.quota_denied",
                    data={
                        "plan": getattr(plan, "value", str(plan)),
                        "monthly_limit": limit,
                        "current_count": count,
                        "route": "POST /receipts",
                    },
                    level="info",
                )
                sentry_set_tags({
                    "quota.exceeded": True,
                    "quota.plan": getattr(plan, "value", str(plan)),
                })
            except Exception:
                pass
            raise HTTPException(status_code=402, detail="Monthly quota exceeded for plan")
    except HTTPException:
        raise
    except Exception:
        # Fail open (never block processing) on internal errors
        pass
    # Dev fallback: if bypass enabled and no Authorization header was sent, ensure we still have a user object.
    if settings.DEV_AUTH_BYPASS and (not request or not request.headers.get("Authorization")):
        # user is already a DB instance from get_user when bypass is True; nothing extra needed
        pass
    # Check file type
    if not file.content_type or not (file.content_type.startswith("image/") or file.content_type == "application/pdf"):
        raise HTTPException(status_code=400, detail="Only image files or PDFs are allowed")
    
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


@router.post("/batch", response_model=List[ReceiptRead])
async def upload_receipts_batch(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> List[ReceiptRead]:
    """Upload multiple receipts in one request.

    Notes:
    - Only image/* files are accepted
    - Max 10 files per request
    - Each file has a 10MB size limit
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Too many files (max 10)")

    # Tier-aware rate limit: per-plan uploads per minute; cost equals number of files
    await enforce_tiered_rate_limit(user, "upload", cost=len(files))

    storage = StorageService()
    created: List[ReceiptRead] = []

    for f in files:
        # Quota check per file (stop early if exceeded)
        try:
            billing = BillingService()
            plan = getattr(user, "plan", None)
            from app.models.enums import PlanType as _PT
            if plan is None:
                plan = _PT.FREE
            now = datetime.utcnow()
            month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
            if now.month == 12:
                next_start = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                next_start = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
            q = select(func.count(Receipt.id)).where(Receipt.owner_id == user.id, Receipt.created_at >= month_start, Receipt.created_at < next_start)
            current_count = (await db.execute(q)).scalar() or 0
            limit = billing.get_monthly_quota(plan)
            if limit != float("inf") and current_count >= limit:
                try:
                    sentry_breadcrumb(
                        category="quota",
                        message="upload_receipts_batch.quota_denied",
                        data={
                            "plan": getattr(plan, "value", str(plan)),
                            "monthly_limit": limit,
                            "current_count": current_count,
                            "route": "POST /receipts/batch",
                        },
                        level="info",
                    )
                    sentry_set_tags({
                        "quota.exceeded": True,
                        "quota.plan": getattr(plan, "value", str(plan)),
                    })
                except Exception:
                    pass
                raise HTTPException(status_code=402, detail="Monthly quota exceeded for plan")
        except HTTPException:
            raise
        except Exception:
            pass
        # Validate content type
        if not f.content_type or not (f.content_type.startswith("image/") or f.content_type == "application/pdf"):
            raise HTTPException(status_code=400, detail=f"Invalid file type (only images or PDFs): {f.filename}")

        # Enforce size limit (10MB)
        contents = await f.read()
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"File too large: {f.filename}")
        # Reset
        f.file.seek(0)

        # Save and create receipt
        file_path, original_filename = await storage.save_upload(f, user.id)

        receipt = Receipt(
            owner_id=user.id,
            file_path=file_path,
            filename=original_filename,
            status=ReceiptStatus.PENDING,
        )
        db.add(receipt)
        await db.commit()
        await db.refresh(receipt)

        # Queue background task
        task_message = extract_and_audit_receipt.send(receipt.id, user.id)
        receipt.task_id = task_message.message_id
        db.add(receipt)
        await db.commit()
        await db.refresh(receipt)

        created.append(ReceiptRead.from_orm(receipt))

    return created


@router.post("/{receipt_id}/reprocess", response_model=ReceiptRead)
async def reprocess_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> ReceiptRead:
    """Requeue background processing for an existing receipt owned by the user."""
    # Tier-aware rate limit: per-plan reprocess per minute
    await enforce_tiered_rate_limit(user, "reprocess", cost=1)
    # Find the receipt and ensure ownership
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Reset minimal fields for reprocessing
    receipt.status = ReceiptStatus.PENDING
    receipt.task_error = None
    receipt.task_retry_count = 0
    receipt.extraction_progress = 0
    receipt.audit_progress = 0
    await db.commit()
    await db.refresh(receipt)
    try:
        _publish_event(user.id, receipt.id, "receipt.reprocess", {
            "status": str(receipt.status.value if hasattr(receipt.status, 'value') else receipt.status),
            "progress": {"extraction": 0, "audit": 0},
        })
    except Exception:
        pass

    # Queue background task
    task_message = extract_and_audit_receipt.send(receipt.id, user.id)
    receipt.task_id = task_message.message_id
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


def _sign_download_token(receipt_id: int, exp_ts: int, secret: str) -> str:
    msg = f"{receipt_id}:{exp_ts}".encode()
    key = secret.encode()
    digest = hmac.new(key, msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


@router.get("/{receipt_id}/download_url")
async def get_receipt_download_url(
    receipt_id: int,
    expires_in: int = 300,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> Dict[str, Any]:
    """Generate a short‑lived signed URL to download the original file."""
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Clamp expires_in to 1 minute .. 1 day
    expires_in = max(60, min(expires_in, 86400))
    exp_ts = int((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp())
    sig = _sign_download_token(receipt.id, exp_ts, settings.SECRET_KEY)
    query = urlencode({"exp": exp_ts, "sig": sig})
    return {"url": f"/receipts/{receipt.id}/download?{query}", "expires_in": expires_in}


@router.get("/{receipt_id}/thumbnail_url")
async def get_receipt_thumbnail_url(
    receipt_id: int,
    expires_in: int = 300,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> Dict[str, Any]:
    """Generate a short‑lived signed URL to download a small thumbnail image."""
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    expires_in = max(60, min(expires_in, 86400))
    exp_ts = int((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp())
    sig = _sign_download_token(receipt.id, exp_ts, settings.SECRET_KEY)
    query = urlencode({"exp": exp_ts, "sig": sig})
    return {"url": f"/receipts/{receipt.id}/thumbnail?{query}", "expires_in": expires_in}


@router.get("/{receipt_id}/download")
async def download_receipt(
    receipt_id: int,
    exp: int,
    sig: str,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
):
    """Stream the original file if token is valid and not expired."""
    # Verify ownership
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts > int(exp):
        raise HTTPException(status_code=401, detail="Link expired")

    expected = _sign_download_token(receipt_id, int(exp), settings.SECRET_KEY)
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Resolve file path and stream
    storage = StorageService()
    full_path = storage.get_full_path(receipt.file_path)
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(full_path),
        filename=receipt.filename or "receipt",
        media_type="application/octet-stream",
    )


@router.get("/{receipt_id}/thumbnail")
async def download_thumbnail(
    receipt_id: int,
    exp: int,
    sig: str,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
):
    """Return a small JPEG thumbnail. Generates on first request and caches on filesystem."""
    # Verify ownership and token
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts > int(exp):
        raise HTTPException(status_code=401, detail="Link expired")
    expected = _sign_download_token(receipt_id, int(exp), settings.SECRET_KEY)
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Load original and generate thumbnail (works for filesystem and MinIO)
    try:
        original_bytes = load_file_from_storage(receipt.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    thumb = generate_thumbnail(original_bytes, receipt.filename)
    if thumb is None:
        # Fallback: just serve original bytes (browser can downscale)
        return Response(content=original_bytes, media_type="application/octet-stream")
    return Response(content=thumb, media_type="image/jpeg")

