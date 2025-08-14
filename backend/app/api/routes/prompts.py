"""API routes for custom prompt templates."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_user, get_clerk_user
from app.models.tables import PromptTemplate
from app.models.schemas import PromptTemplateCreate, PromptTemplateUpdate, PromptTemplateRead


router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=List[PromptTemplateRead])
async def list_prompts(
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_clerk_user),
) -> List[PromptTemplateRead]:
    """List prompt templates belonging to the current user."""
    query = PromptTemplate.__table__.select().where(
        (PromptTemplate.owner_id == user.id) | (PromptTemplate.organisation_id.in_([org.id for org in getattr(user, "organisations", [])]))
    )
    result = await db.execute(query)
    rows = result.fetchall()
    return [PromptTemplateRead(**row._mapping) for row in rows]


@router.post("", response_model=PromptTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_prompt(
    payload: PromptTemplateCreate,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> PromptTemplateRead:
    """Create a new prompt template for extraction, audit or evaluation."""
    prompt = PromptTemplate(
        owner_id=user.id,
        organisation_id=None,
        name=payload.name,
        type=payload.type,
        content=payload.content,
    )
    db.add(prompt)
    await db.commit()
    await db.refresh(prompt)
    return PromptTemplateRead(**prompt.__dict__)


@router.put("/{prompt_id}", response_model=PromptTemplateRead)
async def update_prompt(
    prompt_id: int,
    payload: PromptTemplateUpdate,
    db: AsyncSession = Depends(get_db_session),
    clerk_user = Depends(get_clerk_user),
) -> PromptTemplateRead:
    """Update an existing prompt template."""
    prompt = await db.get(PromptTemplate, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    from app.models.tables import User
    owner = await db.get(User, prompt.owner_id) if prompt.owner_id else None
    from app.api.dependencies import require_owner_or_admin, require_role
    if owner:
        require_owner_or_admin(clerk_user, owner.clerk_id)
    elif prompt.organisation_id:
        require_role(clerk_user, "admin")
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    if payload.name is not None:
        prompt.name = payload.name
    if payload.content is not None:
        prompt.content = payload.content
    await db.commit()
    await db.refresh(prompt)
    return PromptTemplateRead(**prompt.__dict__)



@router.get("/{prompt_id}", response_model=PromptTemplateRead)
async def get_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> PromptTemplateRead:
    """Get a single prompt template by ID."""
    prompt = await db.get(PromptTemplate, prompt_id)
    if not prompt or (prompt.owner_id != user.id and prompt.organisation_id not in [org.id for org in getattr(user, "organisations", [])]):
        raise HTTPException(status_code=404, detail="Prompt not found")
    return PromptTemplateRead(**prompt.__dict__)


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db_session),
    clerk_user = Depends(get_clerk_user),
):
    """Delete a prompt template."""
    prompt = await db.get(PromptTemplate, prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    from app.models.tables import User
    owner = await db.get(User, prompt.owner_id) if prompt.owner_id else None
    from app.api.dependencies import require_owner_or_admin, require_role
    if owner:
        require_owner_or_admin(clerk_user, owner.clerk_id)
    elif prompt.organisation_id:
        require_role(clerk_user, "admin")
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(prompt)
    await db.commit()