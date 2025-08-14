
"""API routes for running and inspecting evaluations."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_user, get_clerk_user
from app.models.tables import Evaluation, EvaluationItem
from app.models.schemas import EvaluationCreate, EvaluationSummary
from app.services.evaluation_service import EvaluationService


router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("", response_model=EvaluationSummary, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    payload: EvaluationCreate,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_clerk_user),
) -> EvaluationSummary:
    """Create a new evaluation run on a set of receipts."""
    service = EvaluationService(db)
    evaluation = await service.create_evaluation(user.id, payload.receipt_ids, payload.model_name)
    return EvaluationSummary.from_orm(evaluation)


@router.get("/{evaluation_id}", response_model=EvaluationSummary)
async def get_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> EvaluationSummary:
    """Retrieve a single evaluation summary."""
    evaluation = await db.get(Evaluation, evaluation_id)
    if not evaluation or evaluation.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return EvaluationSummary.from_orm(evaluation)


@router.get("/{evaluation_id}/items", response_model=List[dict])
async def list_evaluation_items(
    evaluation_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> List[dict]:
    """Return all items for a given evaluation."""
    evaluation = await db.get(Evaluation, evaluation_id)
    if not evaluation or evaluation.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    query = EvaluationItem.__table__.select().where(EvaluationItem.evaluation_id == evaluation_id)
    result = await db.execute(query)
    rows = result.fetchall()
    items = []
    for row in rows:
        data = row._mapping
        items.append({
            "receipt_id": data["receipt_id"],
            "predicted_receipt_details": data["predicted_receipt_details"],
            "predicted_audit_decision": data["predicted_audit_decision"],
            "correct_receipt_details": data["correct_receipt_details"],
            "correct_audit_decision": data["correct_audit_decision"],
            "grader_scores": data["grader_scores"],
        })
    return items



# --- CRUD endpoints for evaluations ---
from app.models.schemas import EvaluationUpdate

@router.get("", response_model=List[EvaluationSummary])
async def list_evaluations(
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> List[EvaluationSummary]:
    """List all evaluations for the current user."""
    query = Evaluation.__table__.select().where(Evaluation.owner_id == user.id)
    result = await db.execute(query)
    rows = result.fetchall()
    return [EvaluationSummary.from_orm(Evaluation(**row._mapping)) for row in rows]

@router.put("/{evaluation_id}", response_model=EvaluationSummary)
async def update_evaluation(
    evaluation_id: int,
    payload: EvaluationUpdate,
    db: AsyncSession = Depends(get_db_session),
    clerk_user = Depends(get_clerk_user),
) -> EvaluationSummary:
    """Update an evaluation (e.g., name, notes)."""
    evaluation = await db.get(Evaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    from app.models.tables import User
    owner = await db.get(User, evaluation.owner_id) if evaluation.owner_id else None
    from app.api.dependencies import require_owner_or_admin
    if owner:
        require_owner_or_admin(clerk_user, owner.clerk_id)
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    if payload.name is not None:
        evaluation.name = payload.name
    if payload.notes is not None:
        evaluation.notes = payload.notes
    await db.commit()
    await db.refresh(evaluation)
    return EvaluationSummary.from_orm(evaluation)

@router.delete("/{evaluation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evaluation(
    evaluation_id: int,
    db: AsyncSession = Depends(get_db_session),
    clerk_user = Depends(get_clerk_user),
):
    """Delete an evaluation."""
    evaluation = await db.get(Evaluation, evaluation_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    from app.models.tables import User
    owner = await db.get(User, evaluation.owner_id) if evaluation.owner_id else None
    from app.api.dependencies import require_owner_or_admin
    if owner:
        require_owner_or_admin(clerk_user, owner.clerk_id)
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(evaluation)
    await db.commit()