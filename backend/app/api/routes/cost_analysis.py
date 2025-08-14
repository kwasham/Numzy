
"""API routes for performing cost analysis on evaluations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_user, get_clerk_user
from app.models.tables import Evaluation, CostAnalysis
from app.models.schemas import CostAnalysisCreate, CostAnalysisRead
from app.services.cost_service import CostService
from typing import List

router = APIRouter(prefix="/cost_analysis", tags=["cost_analysis"])


@router.post("", response_model=CostAnalysisRead, status_code=status.HTTP_201_CREATED)
async def create_cost_analysis(
    payload: CostAnalysisCreate,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_clerk_user),
) -> CostAnalysisRead:
    """Create a cost analysis based on evaluation metrics and cost parameters."""
    evaluation = await db.get(Evaluation, payload.evaluation_id)
    if not evaluation or evaluation.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    service = CostService(db)
    result = await service.analyse(
        evaluation_id=payload.evaluation_id,
        false_positive_rate=payload.false_positive_rate,
        false_negative_rate=payload.false_negative_rate,
        per_receipt_cost=payload.per_receipt_cost,
        audit_cost_per_receipt=payload.audit_cost_per_receipt,
        missed_audit_penalty=payload.missed_audit_penalty,
    )
    # Persist cost analysis
    cost = CostAnalysis(
        evaluation_id=payload.evaluation_id,
        parameters={
            "false_positive_rate": payload.false_positive_rate,
            "false_negative_rate": payload.false_negative_rate,
            "per_receipt_cost": payload.per_receipt_cost,
            "audit_cost_per_receipt": payload.audit_cost_per_receipt,
            "missed_audit_penalty": payload.missed_audit_penalty,
        },
        result=result,
    )
    db.add(cost)
    await db.commit()
    await db.refresh(cost)
    return CostAnalysisRead.from_orm(cost)


@router.get("", response_model=List[CostAnalysisRead])
async def list_cost_analyses(
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> List[CostAnalysisRead]:
    """List all cost analyses for the current user."""
    query = CostAnalysis.__table__.select()
    result = await db.execute(query)
    rows = result.fetchall()
    # Only return cost analyses for evaluations owned by the user
    filtered = []
    for row in rows:
        cost = CostAnalysis(**row._mapping)
        evaluation = await db.get(Evaluation, cost.evaluation_id)
        if evaluation and evaluation.owner_id == user.id:
            filtered.append(CostAnalysisRead.from_orm(cost))
    return filtered


@router.get("/{cost_analysis_id}", response_model=CostAnalysisRead)
async def get_cost_analysis(
    cost_analysis_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> CostAnalysisRead:
    """Get a single cost analysis by ID."""
    cost = await db.get(CostAnalysis, cost_analysis_id)
    if not cost:
        raise HTTPException(status_code=404, detail="Cost analysis not found")
    evaluation = await db.get(Evaluation, cost.evaluation_id)
    if not evaluation or evaluation.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return CostAnalysisRead.from_orm(cost)


@router.put("/{cost_analysis_id}", response_model=CostAnalysisRead)
async def update_cost_analysis(
    cost_analysis_id: int,
    payload: CostAnalysisCreate,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> CostAnalysisRead:
    """Update a cost analysis."""
    cost = await db.get(CostAnalysis, cost_analysis_id)
    if not cost:
        raise HTTPException(status_code=404, detail="Cost analysis not found")
    evaluation = await db.get(Evaluation, cost.evaluation_id)
    if not evaluation or evaluation.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    # Update parameters and result
    cost.parameters = {
        "false_positive_rate": payload.false_positive_rate,
        "false_negative_rate": payload.false_negative_rate,
        "per_receipt_cost": payload.per_receipt_cost,
        "audit_cost_per_receipt": payload.audit_cost_per_receipt,
        "missed_audit_penalty": payload.missed_audit_penalty,
    }
    service = CostService(db)
    cost.result = await service.analyse(
        evaluation_id=payload.evaluation_id,
        false_positive_rate=payload.false_positive_rate,
        false_negative_rate=payload.false_negative_rate,
        per_receipt_cost=payload.per_receipt_cost,
        audit_cost_per_receipt=payload.audit_cost_per_receipt,
        missed_audit_penalty=payload.missed_audit_penalty,
    )
    await db.commit()
    await db.refresh(cost)
    return CostAnalysisRead.from_orm(cost)


@router.delete("/{cost_analysis_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cost_analysis(
    cost_analysis_id: int,
    db: AsyncSession = Depends(get_db_session),
    clerk_user = Depends(get_clerk_user),
):
    """Delete a cost analysis."""
    cost = await db.get(CostAnalysis, cost_analysis_id)
    if not cost:
        raise HTTPException(status_code=404, detail="Cost analysis not found")
    evaluation = await db.get(Evaluation, cost.evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    from app.models.tables import User
    owner = await db.get(User, evaluation.owner_id) if evaluation.owner_id else None
    from app.api.dependencies import require_owner_or_admin
    if owner:
        require_owner_or_admin(clerk_user, owner.clerk_id)
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(cost)
    await db.commit()