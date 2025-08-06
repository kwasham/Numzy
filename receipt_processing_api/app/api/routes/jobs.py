"""API routes for background job tracking."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from app.api.dependencies import get_db_session, get_user
from app.models.tables import BackgroundJob, User

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobResponse(BaseModel):
    """Background job status response."""
    id: str
    job_type: str
    status: str
    progress: int
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    receipt_id: Optional[int] = None
    
    class Config:
        from_attributes = True


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_user),
) -> JobResponse:
    """Get status and progress of a background job."""
    stmt = select(BackgroundJob).where(
        and_(
            BackgroundJob.id == job_id,
            BackgroundJob.user_id == user.id
        )
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse.from_orm(job)


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_user),
) -> List[JobResponse]:
    """List background jobs for the current user."""
    stmt = select(BackgroundJob).where(
        BackgroundJob.user_id == user.id
    )
    
    if status:
        stmt = stmt.where(BackgroundJob.status == status)
    
    stmt = stmt.order_by(BackgroundJob.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    
    return [JobResponse.from_orm(job) for job in jobs]


@router.delete("/{job_id}", status_code=204)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_user),
):
    """Cancel a pending or running job."""
    stmt = select(BackgroundJob).where(
        and_(
            BackgroundJob.id == job_id,
            BackgroundJob.user_id == user.id
        )
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status in ["completed", "failed"]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed or failed job")
    
    # Cancel the Dramatiq job
    from app.core.tasks import extract_and_audit_receipt
    try:
        extract_and_audit_receipt.message().cancel()
    except Exception:
        pass  # Job might already be running
    
    # Update job status
    job.status = "cancelled"
    job.completed_at = datetime.utcnow()
    await db.commit()
    
    return None