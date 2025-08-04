"""API routes for managing audit rules."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_user, get_clerk_user, get_audit_service, get_current_user
from app.models.tables import AuditRule, User, PromptTemplate
from app.models.schemas import AuditRuleNLCreate, PromptTemplateCreate, AuditRuleCreate, AuditRuleUpdate, AuditRuleRead
from app.services.audit_service import AuditService 
from app.services.prompt_templates import prompt_template_repository
from app.models.enums import RuleType


router = APIRouter(prefix="/audit_rules", tags=["audit_rules"])


@router.get("", response_model=List[AuditRuleRead])
async def list_audit_rules(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),
) -> List[AuditRuleRead]:
    """List all audit rules for the current user."""
    from sqlalchemy import select
    
    # Build a query to select rules belonging to the user
    # For now, just get rules owned by the user (ignore organizations)
    query = select(AuditRule).where(AuditRule.owner_id == user.id)
    
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return [AuditRuleRead.model_validate(rule, from_attributes=True) for rule in rules]


# receipt_processing_api/app/api/routes/audit_rules.py

@router.post("/nl", response_model=AuditRuleRead)
async def create_nl_audit_rule(
    rule: AuditRuleNLCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AuditRuleRead:
    """Create an audit rule from natural language description."""
    # Create audit service instance without passing db
    service = AuditService()
    
    # Get audit instructions from MCP
    instructions = await service._get_audit_instructions(rule.description, rule.threshold)
    
    
    # Create the prompt template directly
    prompt_template = PromptTemplate(
        name=f"{rule.name}_prompt",
        type="audit",
        content=instructions,
        owner_id=current_user.id,
    )
    db.add(prompt_template)
    await db.commit()
    await db.refresh(prompt_template)
    
    # Create the audit rule
    audit_rule = AuditRule(
        name=rule.name,
        type=RuleType.LLM,
        owner_id=current_user.id,
        config={"prompt_id": prompt_template.id, "threshold": rule.threshold},
        active=True,
    )
    
    db.add(audit_rule)
    await db.commit()
    await db.refresh(audit_rule)
    
    return AuditRuleRead(**audit_rule.__dict__)  # Use AuditRuleRead



@router.post("", response_model=AuditRuleRead, status_code=status.HTTP_201_CREATED)
async def create_audit_rule(
    payload: AuditRuleCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),  # Change to get_current_user
) -> AuditRuleRead:
    """Create a new audit rule for the user."""
    from sqlalchemy import select
    
    # Simple plan enforcement: limit number of rules for free tier
    existing_query = select(AuditRule).where(AuditRule.owner_id == user.id)
    existing_result = await db.execute(existing_query)
    existing_rules = existing_result.scalars().all()
    
    if user.plan.value == "free" and len(existing_rules) >= 0:
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
    return AuditRuleRead.model_validate(rule, from_attributes=True)


@router.put("/{rule_id}", response_model=AuditRuleRead)
async def update_audit_rule(
    rule_id: int,
    payload: AuditRuleUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),  # Change to get_current_user
) -> AuditRuleRead:
    """Update an existing audit rule."""
    rule = await db.get(AuditRule, rule_id)
    if not rule or rule.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Audit rule not found")
    if payload.name is not None:
        rule.name = payload.name
    if payload.config is not None:
        rule.config = payload.config
    if payload.active is not None:
        rule.active = payload.active
    await db.commit()
    await db.refresh(rule)
    return AuditRuleRead.model_validate(rule, from_attributes=True)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),  # Change to get_current_user
):
    """Delete an audit rule."""
    rule = await db.get(AuditRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Audit rule not found")
    
    # Simplified authorization check for dev mode
    if rule.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.delete(rule)
    await db.commit()


@router.get("/{rule_id}", response_model=AuditRuleRead)
async def get_audit_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(get_current_user),  # Change to get_current_user
) -> AuditRuleRead:
    """Retrieve a single audit rule by ID."""
    rule = await db.get(AuditRule, rule_id)
    if not rule or rule.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Audit rule not found")
    return AuditRuleRead.model_validate(rule, from_attributes=True)