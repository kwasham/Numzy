"""API routes for receipt upload and retrieval."""

from __future__ import annotations

import os
from typing import List, Dict, Any
from datetime import datetime, timezone, timedelta
import hmac
import hashlib
import base64
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Request, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
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
from app.services.cache import cache_get_json, cache_set_json
from app.utils.image_processing import generate_thumbnail
from app.core.tasks import extract_and_audit_receipt
from app.core.tasks import _publish_event  # lightweight publisher
from app.services.cache import (
    cache_get_json,
    cache_set_json,
    invalidate_receipts_summary,
    invalidate_receipt_detail,
    summary_cache_key,
    detail_cache_key,
)
import asyncio
import json
import httpx
from app.core.security import decode_clerk_jwt, CLERK_SECRET_KEY, CLERK_API_URL
from app.models.enums import PlanType

router = APIRouter(prefix="/receipts", tags=["receipts"])


# ---------------------------------------------------------------------------
# Optional query-token authentication helper (parity with SSE stream endpoint)
# ---------------------------------------------------------------------------
async def user_with_optional_token(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    token: str | None = Query(None),
):
    """Authenticate via Authorization header or `?token=` query using Clerk JWT.

    - Requires a valid Bearer token (or `?token=`).
    - Decodes JWT via Clerk JWKS.
    - Resolves existing local user by `clerk_id`, or fetches from Clerk API and creates/backfills.
    - No development bypass or synthetic users.
    """
    # Extract token from header or query param
    auth_header = request.headers.get("Authorization")
    bearer_token = auth_header.split(" ", 1)[1] if auth_header and auth_header.startswith("Bearer ") else None
    jwt_token = bearer_token or token
    if not jwt_token:
        raise HTTPException(status_code=401, detail="Missing auth token")

    # Verify token and extract Clerk user id
    payload = decode_clerk_jwt(jwt_token)
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Invalid Clerk token: no sub claim")

    # Fast path: existing by clerk_id
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if user:
        return user

    # Need Clerk secret for user lookup when first seen
    if not CLERK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Clerk secret key not configured")

    # Fetch user from Clerk to populate email/name
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(
            f"{CLERK_API_URL}/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Clerk user not found")
    clerk_user = resp.json()
    email = (
        clerk_user.get("email_addresses", [{}])[0].get("email_address")
        or clerk_user.get("email_address")
    )
    first = clerk_user.get("first_name", "")
    last = clerk_user.get("last_name", "")
    name = f"{first} {last}".strip() or email
    if not email:
        raise HTTPException(status_code=400, detail="Clerk user missing email")

    # Backfill existing user by email or create
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        if not getattr(user, "clerk_id", None):
            user.clerk_id = clerk_user_id  # type: ignore[attr-defined]
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

    user = User(email=email, name=name, clerk_id=clerk_user_id, plan=PlanType.FREE)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("", response_model=ReceiptRead)
async def upload_receipt(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(user_with_optional_token),
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
    
    # Invalidate summary caches (new receipt affects list) but do not await pattern deletion inline (fire & forget)
    try:
        import asyncio as _asyncio
        _asyncio.create_task(invalidate_receipts_summary(user.id))
    except Exception:
        pass
    return ReceiptRead.from_orm(receipt)


@router.post("/batch", response_model=List[ReceiptRead])
async def upload_receipts_batch(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(user_with_optional_token),
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
    user: User = Depends(user_with_optional_token),
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

    # Invalidate caches for this receipt + summaries
    try:
        import asyncio as _asyncio
        _asyncio.create_task(invalidate_receipt_detail(user.id, receipt.id))
        _asyncio.create_task(invalidate_receipts_summary(user.id))
    except Exception:
        pass
    return ReceiptRead.from_orm(receipt)


@router.get("", response_model=List[ReceiptRead])
async def list_receipts(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(user_with_optional_token),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[ReceiptRead]:
    """List receipts for the current user (paged). Falls back to full list if under limit.

    Note: This preserves backwards compatibility but now offers pagination.
    """
    query = select(Receipt).where(Receipt.owner_id == user.id).order_by(Receipt.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    receipts = result.scalars().all()
    return receipts


class ReceiptSummary(BaseModel):
    id: int
    filename: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime | None = None
    extraction_progress: int | None = 0
    audit_progress: int | None = 0
    # minimal merchant & total hints (optional)
    merchant: str | None = None
    total: float | None = None
    # minimal payment method hints
    payment_type: str | None = None
    payment_brand: str | None = None
    payment_last4: str | None = None
    # (NEW) include extracted_data so the frontend can fully hydrate the modal without an extra fetch
    extracted_data: dict | None = None


@router.get("/summary", response_model=List[ReceiptSummary])
async def list_receipts_summary(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(user_with_optional_token),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: str | None = Query(
        None,
        description="Optional status filter (e.g. 'processing', 'completed')."
    ),
) -> List[ReceiptSummary]:
    """Fast summary list with Redis caching (60s TTL after recent change).

    Returns only minimal fields required for the table first paint. Supports optional status filter.
    """
    # Incorporate status into cache key to avoid returning unfiltered results
    base_key = summary_cache_key(user.id, limit, offset)
    cache_key = f"{base_key}:status={status}" if status else base_key
    cached = await cache_get_json(cache_key)
    if isinstance(cached, list):  # shape already JSON
        try:
            return [ReceiptSummary(**item) for item in cached]
        except Exception:
            pass  # ignore malformed cache
    # Build base query (only required columns);
    query = select(
        Receipt.id,
        Receipt.filename,
        Receipt.status,
        Receipt.created_at,
        Receipt.updated_at,
        Receipt.extraction_progress,
        Receipt.audit_progress,
        Receipt.extracted_data,
        # Note: we include extracted_data column so the client can render modal immediately.
    ).where(Receipt.owner_id == user.id)
    if status:
        query = query.where(Receipt.status == status)
    query = query.order_by(Receipt.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    

    summaries: list[ReceiptSummary] = []
    for row in rows:
        # row is Row(tuple) -> destructure; avoid shadowing filter param 'status'
        (rid, fname, row_status, created_at, updated_at, extraction_progress, audit_progress, extracted_data) = row
        merchant = None
        total = None
        payment_type = None
        payment_brand = None
        payment_last4 = None
        try:
            if isinstance(extracted_data, dict):
                merchant = (
                    extracted_data.get("merchant")
                    or extracted_data.get("vendor")
                    or extracted_data.get("merchant_name")
                )
                total_raw = (
                    extracted_data.get("total")
                    or extracted_data.get("amount_total")
                    or extracted_data.get("amount")
                )
                if isinstance(total_raw, (int, float)):
                    total = float(total_raw)
                elif isinstance(total_raw, str):
                    # simple parse removing non numeric except . -
                    import re
                    try:
                        num = re.sub(r"[^0-9.+-]", "", total_raw)
                        if num:
                            total = float(num)
                    except Exception:
                        pass
                # payment inference (mirror frontend logic but minimal)
                pm_source = (
                    extracted_data.get("payment_method")
                    or extracted_data.get("payment")
                    or extracted_data.get("card")
                )
                if isinstance(pm_source, dict):
                    raw_brand = (
                        pm_source.get("brand")
                        or pm_source.get("type")
                        or pm_source.get("card_brand")
                        or pm_source.get("scheme")
                        or pm_source.get("network")
                        or ""
                    )
                    norm = str(raw_brand).lower().replace(" ", "").replace("-", "").replace("_", "")
                    brand_map = {
                        "visa": "visa",
                        "mastercard": "mastercard",
                        "mc": "mastercard",
                        "americanexpress": "amex",
                        "amex": "amex",
                        "applepay": "applepay",
                        "apple": "applepay",
                        "googlepay": "googlepay",
                        "google": "googlepay",
                    }
                    p_type = brand_map.get(norm) or (norm or None)
                    last4 = (
                        pm_source.get("last4")
                        or pm_source.get("card_last4")
                        or (
                            pm_source.get("number")
                            and str(pm_source.get("number")).isdigit()
                            and str(pm_source.get("number")).strip()[-4:]
                        )
                        or (
                            pm_source.get("card_number")
                            and str(pm_source.get("card_number")).isdigit()
                            and str(pm_source.get("card_number")).strip()[-4:]
                        )
                    )
                    payment_type = p_type  # normalized brand/type
                    payment_brand = p_type
                    payment_last4 = last4 if last4 else None
        except Exception:
            pass
        summaries.append(
            ReceiptSummary(
                id=rid,
                filename=fname,
                status=row_status,
                created_at=created_at,
                updated_at=updated_at,
                extraction_progress=extraction_progress or 0,
                audit_progress=audit_progress or 0,
                merchant=merchant,
                total=total,
                payment_type=payment_type,
                payment_brand=payment_brand,
                payment_last4=payment_last4,
                extracted_data=extracted_data if isinstance(extracted_data, dict) else None,
            )
        )
    return summaries


@router.get("/events", include_in_schema=False)
async def receipt_events(
    request: Request,
    user = Depends(get_user),
):
    """Server-Sent Events stream of receipt status/progress updates for the authenticated user.

    Relays Redis pub/sub messages published on channel receipts:user:{user_id}.
    """
    try:
        import redis.asyncio as aioredis  # type: ignore
    except Exception:  # pragma: no cover
        raise HTTPException(status_code=503, detail="Events backend unavailable")

    channel = f"receipts:user:{user.id}"
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(channel)

    async def event_generator():  # type: ignore
        try:
            while True:
                if await request.is_disconnected():
                    break
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if msg and msg.get("type") == "message":
                    data = msg.get("data")
                    # Ensure each event is a single line JSON
                    yield f"data: {data}\n\n"
                # Cooperative sleep to avoid tight loop
                await asyncio.sleep(0.05)
        finally:
            with contextlib.suppress(Exception):  # type: ignore
                await pubsub.unsubscribe(channel)
                await pubsub.close()
            with contextlib.suppress(Exception):  # type: ignore
                await client.close()

    import contextlib  # local import to avoid global dependency
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)


@router.get("/{receipt_id}", response_model=ReceiptRead)
async def get_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(user_with_optional_token),
) -> ReceiptRead:
    """Get a specific receipt by ID."""
    # Try cache first
    ck = detail_cache_key(user.id, receipt_id)
    cached = await cache_get_json(ck)
    if isinstance(cached, dict):
        try:
            return ReceiptRead(**cached)
        except Exception:
            pass
    query = select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id)
    result = await db.execute(query)
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    # Cache minimal period (5s)
    try:
        # Increase detail cache TTL for 60 seconds to reduce backend load
        await cache_set_json(ck, ReceiptRead.from_orm(receipt).dict(), ttl=60)
    except Exception:
        pass
    return receipt


@router.patch("/{receipt_id}", response_model=ReceiptRead)
async def update_receipt(
    receipt_id: int,
    update_data: ReceiptUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(user_with_optional_token),
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
    # Invalidate caches
    try:
        import asyncio as _asyncio
        _asyncio.create_task(invalidate_receipt_detail(user.id, receipt.id))
        _asyncio.create_task(invalidate_receipts_summary(user.id))
    except Exception:
        pass
    return receipt


@router.delete("/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receipt(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(user_with_optional_token),
):  # Remove the return type annotation
    """Delete a receipt."""
    query = select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id)
    result = await db.execute(query)
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    rid = receipt.id
    await db.delete(receipt)
    await db.commit()
    try:
        import asyncio as _asyncio
        _asyncio.create_task(invalidate_receipt_detail(user.id, rid))
        _asyncio.create_task(invalidate_receipts_summary(user.id))
    except Exception:
        pass
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
    user: User = Depends(user_with_optional_token),
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
async def get_download_url(
    receipt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(user_with_optional_token),
) -> dict[str, Any]:
    """Return a short‑lived signed URL to stream the original file via this API."""
    # Enforce ownership
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if not receipt.file_path:
        raise HTTPException(status_code=409, detail="File not ready")
    # Ensure file exists, then sign local route
    storage = StorageService()
    try:
        if getattr(storage, "backend", "").lower() == "minio" and hasattr(storage, "_client"):
            storage._client.stat_object(storage.bucket, receipt.file_path)  # type: ignore[attr-defined]
        else:
            full_path = storage.get_full_path(receipt.file_path)
            if not full_path.exists():
                raise FileNotFoundError
    except Exception:
        raise HTTPException(status_code=409, detail="File not ready")
    expires_in = 300
    exp_ts = int((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp())
    sig = _sign_download_token(receipt.id, exp_ts, settings.SECRET_KEY)
    q = urlencode({"exp": exp_ts, "sig": sig})
    return {"url": f"/receipts/{receipt.id}/download?{q}", "expires_in": expires_in}


@router.get("/{receipt_id}/thumbnail_url")
async def get_receipt_thumbnail_url(
    receipt_id: int,
    expires_in: int = 300,
    db: AsyncSession = Depends(get_db_session),
    user: User | None = Depends(user_with_optional_token),
) -> Dict[str, Any]:
    """Generate a short‑lived signed URL to fetch a small thumbnail via this API."""
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id, Receipt.owner_id == user.id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if not receipt.file_path:
        raise HTTPException(status_code=409, detail="Receipt file not ready")
    # Ensure file exists, then sign local route
    storage = StorageService()
    try:
        if getattr(storage, "backend", "").lower() == "minio" and hasattr(storage, "_client"):
            storage._client.stat_object(storage.bucket, receipt.file_path)  # type: ignore[attr-defined]
        else:
            full_path = storage.get_full_path(receipt.file_path)
            if not full_path.exists():
                raise FileNotFoundError
    except Exception:
        raise HTTPException(status_code=409, detail="Receipt file not ready")
    expires_in = max(60, min(int(expires_in or 300), 86400))
    exp_ts = int((datetime.now(timezone.utc) + timedelta(seconds=expires_in)).timestamp())
    sig = _sign_download_token(receipt.id, exp_ts, settings.SECRET_KEY)
    q = urlencode({"exp": exp_ts, "sig": sig})
    return {"url": f"/receipts/{receipt.id}/thumbnail?{q}", "expires_in": expires_in, "cached": True}


@router.get("/{receipt_id}/download")
async def download_receipt(
    receipt_id: int,
    exp: int,
    sig: str,
    db: AsyncSession = Depends(get_db_session),
    # removed auth dependency to allow browser fetch without Authorization header
):
    """Stream the original file if token is valid and not expired.

    Uses HMAC-signed, short-lived token, so no Authorization header is required.
    """
    # Verify token timing and signature
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts > int(exp):
        raise HTTPException(status_code=401, detail="Link expired")

    expected = _sign_download_token(receipt_id, int(exp), settings.SECRET_KEY)
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Load receipt by id only; access is controlled by the signed token
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    storage = StorageService()
    # MinIO backend: stream object directly (avoid filesystem-only base_dir attribute)
    if getattr(storage, "backend", "").lower() == "minio" and hasattr(storage, "_client"):
        try:
            resp = storage._client.get_object(storage.bucket, receipt.file_path)  # type: ignore[attr-defined]
        except Exception:
            raise HTTPException(status_code=404, detail="File not found")
        # We must stream the body out; wrap in StreamingResponse to control close
        from fastapi.responses import StreamingResponse

        async def iter_body():  # type: ignore[no-untyped-def]
            try:
                while True:
                    chunk = resp.read(8192)  # type: ignore[attr-defined]
                    if not chunk:
                        break
                    yield chunk
            finally:  # ensure connection release
                try:
                    resp.close()  # type: ignore[attr-defined]
                    resp.release_conn()  # type: ignore[attr-defined]
                except Exception:
                    pass

        return StreamingResponse(
            iter_body(),
            media_type="application/octet-stream",
            # Sanitize filename to avoid header injection / syntax issues; avoid backslashes and quotes
            headers={
                "Content-Disposition": (
                    lambda _name: f"attachment; filename=\"{_name}\""
                )(
                    (receipt.filename or "receipt").replace("\\", "_").replace("\"", "")
                )
            },
        )

    # Filesystem backend
    try:
        full_path = storage.get_full_path(receipt.file_path)
    except AttributeError:
        # base_dir missing means misconfigured storage; surface 500 to client
        raise HTTPException(status_code=500, detail="Storage backend misconfigured (no base_dir)")
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=str(full_path), filename=receipt.filename or "receipt", media_type="application/octet-stream")


@router.get("/{receipt_id}/thumbnail")
async def download_thumbnail(
    receipt_id: int,
    exp: int,
    sig: str,
    db: AsyncSession = Depends(get_db_session),
    # removed auth dependency to allow browser fetch without Authorization header
):
    """Return a small JPEG thumbnail. Generates on first request and caches on filesystem.

    Uses HMAC-signed, short-lived token, so no Authorization header is required.
    """
    # Verify token timing and signature
    now_ts = int(datetime.now(timezone.utc).timestamp())
    if now_ts > int(exp):
        raise HTTPException(status_code=401, detail="Link expired")
    expected = _sign_download_token(receipt_id, int(exp), settings.SECRET_KEY)
    if not hmac.compare_digest(expected, sig):
        raise HTTPException(status_code=401, detail="Invalid token")

    # Load receipt by id only; access is controlled by the signed token
    result = await db.execute(select(Receipt).where(Receipt.id == receipt_id))
    receipt = result.scalar_one_or_none()
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    # Attempt cached thumbnail (Redis) first
    cache_key = f"receipts:thumb:{receipt_id}"
    try:
        cached = await cache_get_json(cache_key)
        if isinstance(cached, str):
            import base64
            try:
                raw = base64.b64decode(cached)
                print(f"[thumbnail] cache-hit id={receipt_id} bytes={len(raw)}")
                return Response(content=raw, media_type="image/jpeg", headers={"x-thumb-stage": "cache-hit"})
            except Exception:
                pass
    except Exception:
        pass
    try:
        original_bytes = load_file_from_storage(receipt.file_path)
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        thumb = generate_thumbnail(original_bytes, receipt.filename)
        if thumb:
            # Store base64 to Redis (<=512KB) for ~60s
            if len(thumb) <= 512 * 1024:
                import base64 as _b64
                try:
                    await cache_set_json(cache_key, _b64.b64encode(thumb).decode(), ttl=60)
                except Exception:
                    pass
            print(f"[thumbnail] generated id={receipt_id} bytes={len(thumb)}")
            return Response(content=thumb, media_type="image/jpeg", headers={
                "x-thumb-stage": "generated",
                "x-thumb-fallback": "0",  # explicit marker that this is NOT a placeholder
            })
    except Exception as e:  # pragma: no cover
        print(f"[thumbnail] generation error id={receipt_id} err={e}")

    # Fallback logic: ensure we still return a renderable image (especially for PDFs)
    filename_lower = (receipt.filename or "").lower()
    # If original is an image type, serve it with an appropriate media type
    if filename_lower.endswith((".jpg", ".jpeg")):
        print(f"[thumbnail] original-image id={receipt_id} bytes={len(original_bytes)}")
        return Response(content=original_bytes, media_type="image/jpeg", headers={
            "x-thumb-stage": "original-image",
            "x-thumb-fallback": "0",
        })
    if filename_lower.endswith(".png"):
        print(f"[thumbnail] original-image id={receipt_id} bytes={len(original_bytes)}")
        return Response(content=original_bytes, media_type="image/png", headers={
            "x-thumb-stage": "original-image",
            "x-thumb-fallback": "0",
        })
    if filename_lower.endswith(".webp"):
        print(f"[thumbnail] original-image id={receipt_id} bytes={len(original_bytes)}")
        return Response(content=original_bytes, media_type="image/webp", headers={
            "x-thumb-stage": "original-image",
            "x-thumb-fallback": "0",
        })
    if filename_lower.endswith(".gif"):
        print(f"[thumbnail] original-image id={receipt_id} bytes={len(original_bytes)}")
        return Response(content=original_bytes, media_type="image/gif", headers={
            "x-thumb-stage": "original-image",
            "x-thumb-fallback": "0",
        })

    # PDF or unknown type: attempt to fabricate a simple placeholder JPEG so the UI has something to show
    if filename_lower.endswith(".pdf"):
        try:  # pragma: no cover - best effort placeholder
            from io import BytesIO
            try:
                from PIL import Image, ImageDraw  # type: ignore
            except Exception:  # Pillow not available (should not happen given requirements)
                Image = None  # type: ignore
                ImageDraw = None  # type: ignore
            if Image is not None:
                img = Image.new("RGB", (480, 360), color=(245, 245, 245))
                if ImageDraw is not None:
                    draw = ImageDraw.Draw(img)
                    text = "PREVIEW\nUNAVAILABLE" if not filename_lower.endswith(".pdf") else "PDF"
                    try:
                        # crude centering / multi-line
                        lines = text.split("\n")
                        y = 140
                        for line in lines:
                            w, h = draw.textsize(line) if hasattr(draw, "textsize") else (60, 20)
                            draw.text(((img.width - w) / 2, y), line, fill=(120, 120, 120))
                            y += h + 4
                    except Exception:
                        pass
                buf = BytesIO()
                img.save(buf, format="JPEG", quality=80)
                data = buf.getvalue()
                print(f"[thumbnail] pdf-placeholder id={receipt_id} bytes={len(data)}")
                return Response(content=data, media_type="image/jpeg", headers={"x-thumb-stage": "pdf-placeholder", "x-thumb-fallback": "pdf"})
        except Exception:
            pass
    # Last resort: fabricate a generic placeholder (avoids endless 204 loop client-side)
    # Attempt Pillow placeholder; if not possible, fall back to embedded 1x1 PNG (transparent)
    try:  # pragma: no cover - best effort visual aid
        from io import BytesIO
        try:
            from PIL import Image, ImageDraw  # type: ignore
        except Exception:  # Pillow missing or no drawing support
            Image = None  # type: ignore
            ImageDraw = None  # type: ignore
        if Image is not None:
            img = Image.new("RGB", (420, 320), color=(245, 245, 245))
            if ImageDraw is not None:
                draw = ImageDraw.Draw(img)
                label = (receipt.filename or "").rsplit("/", 1)[-1]
                ext = label.split(".")[-1][:10].upper() if "." in label else ""
                text = "NO PREVIEW" + (f"\n{ext}" if ext else "")
                y = 120
                for line in text.split("\n"):
                    try:
                        w, h = draw.textsize(line) if hasattr(draw, "textsize") else (60, 20)
                        draw.text(((img.width - w) / 2, y), line, fill=(120, 120, 120))
                        y += h + 6
                    except Exception:
                        continue
            buf = BytesIO()
            img.save(buf, format="JPEG", quality=80)
            data = buf.getvalue()
            print(f"[thumbnail] generic-placeholder id={receipt_id} bytes={len(data)}")
            return Response(content=data, media_type="image/jpeg", headers={"x-thumb-stage": "generic-placeholder", "x-thumb-fallback": "pillow"})
    except Exception:
        pass
    # Base64 1x1 PNG (transparent)
    import base64
    tiny_png = base64.b64decode(
        b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB/af8w8sAAAAASUVORK5CYII="
    )
    print(f"[thumbnail] tiny-fallback id={receipt_id} bytes={len(tiny_png)}")
    return Response(content=tiny_png, media_type="image/png", headers={"x-thumb-stage": "tiny-fallback", "x-thumb-fallback": "embedded"})

