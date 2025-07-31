"""API routes for managing audit rules."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_user, get_clerk_user, get_audit_service
from app.models.tables import AuditRule
from app.models.schemas import AuditRuleNLCreate, PromptTemplateCreate, AuditRuleCreate, AuditRuleUpdate, AuditRuleRead
from app.services.audit_service import AuditService 
from app.services.prompt_templates import prompt_template_repository
from app.models.enums import RuleType


router = APIRouter(prefix="/audit_rules", tags=["audit_rules"])


@router.get("", response_model=List[AuditRuleRead])
async def list_audit_rules(
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_clerk_user),
) -> List[AuditRuleRead]:
    """List all audit rules for the current user."""
    # Build a query to select rules belonging to the user or their organisations
    org_ids = [org.id for org in getattr(user, "organisations", [])]
    query = AuditRule.__table__.select().where(
        (AuditRule.owner_id == user.id) | (AuditRule.organisation_id.in_(org_ids))
    )
    result = await db.execute(query)
    rows = result.fetchall()
    return [AuditRuleRead(**row._mapping) for row in rows]


# receipt_processing_api/app/api/routes/audit_rules.py

@router.post("/nl", response_model=AuditRuleRead)
async def create_nl_audit_rule(
    rule: AuditRuleNLCreate,
    service: AuditService = Depends(get_audit_service),
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user)
) -> AuditRuleRead:
    """
    Accept a natural-language rule description, generate a prompt using the MCP server,
    and store it as a PromptTemplate.
    """
    
    # Generate instructions from the prompt server
    instructions = await service._get_audit_instructions(rule.description, rule.threshold)

    # Save instructions as a prompt template; adjust fields as needed
    saved_prompt = await prompt_template_repository.create(
        PromptTemplateCreate(
            name=rule.name,
            content=instructions,
            type="audit",
            owner_id=user.id,
            organisation_id=None,
        )
    )

    # After saving the prompt
    new_rule = AuditRule(
        owner_id=user.id,
        name=rule.name,
        type=RuleType.LLM,
        config={"prompt_id": saved_prompt.id, "threshold": rule.threshold},
        active=True,
    )
    db.add(new_rule)
    await db.commit()
    await db.refresh(new_rule)
    return AuditRuleRead(**new_rule.__dict__)



@router.post("", response_model=AuditRuleRead, status_code=status.HTTP_201_CREATED)
async def create_audit_rule(
    payload: AuditRuleCreate,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> AuditRuleRead:
    """Create a new audit rule for the user."""
    # Simple plan enforcement: limit number of rules for free tier
    existing_query = AuditRule.__table__.select().where(AuditRule.owner_id == user.id)
    existing_rows = (await db.execute(existing_query)).fetchall()
    if user.plan.value == "free" and len(existing_rows) >= 0:
        # Free plan cannot create custom rules (only default ones)
        raise HTTPException(status_code=403, detail="Free plan cannot create custom rules")
    rule = AuditRule(
        owner_id=user.id,
        organisation_id=None,
        name=payload.name,
        type=payload.type,
        config=payload.config,
        active=payload.active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return AuditRuleRead(**rule.__dict__)


@router.put("/{rule_id}", response_model=AuditRuleRead)
async def update_audit_rule(
    rule_id: int,
    payload: AuditRuleUpdate,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> AuditRuleRead:
    """Update an existing audit rule."""
    rule = await db.get(AuditRule, rule_id)
    if not rule or (rule.owner_id != user.id and rule.organisation_id not in [org.id for org in user.organisations]):
        raise HTTPException(status_code=404, detail="Audit rule not found")
    if payload.name is not None:
        rule.name = payload.name
    if payload.config is not None:
        rule.config = payload.config
    if payload.active is not None:
        rule.active = payload.active
    await db.commit()
    await db.refresh(rule)
    return AuditRuleRead(**rule.__dict__)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db_session),
    clerk_user = Depends(get_clerk_user),
):
    """Delete an audit rule."""
    rule = await db.get(AuditRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Audit rule not found")
    # Get owner's clerk_id
    from app.models.tables import User
    owner = await db.get(User, rule.owner_id) if rule.owner_id else None
    from app.api.dependencies import require_owner_or_admin, require_role
    if owner:
        require_owner_or_admin(clerk_user, owner.clerk_id)
    elif rule.organisation_id:
        require_role(clerk_user, "admin")
    else:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.delete(rule)
    await db.commit()


@router.get("/{rule_id}", response_model=AuditRuleRead)
async def get_audit_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> AuditRuleRead:
    """Retrieve a single audit rule by ID."""
    rule = await db.get(AuditRule, rule_id)
    if not rule or (rule.owner_id != user.id and rule.organisation_id not in [org.id for org in getattr(user, "organisations", [])]):
        raise HTTPException(status_code=404, detail="Audit rule not found")
    return AuditRuleRead(**rule.__dict__)