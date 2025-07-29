

"""API routes for managing organisations (teams)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_user, get_clerk_user
from app.models.tables import Organisation
from app.models.enums import PlanType


router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("", response_model=List[dict])
async def list_teams(
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_clerk_user),
) -> List[dict]:
    """Return a list of organisations the user belongs to."""
    orgs = getattr(user, "organisations", [])
    return [
        {
            "id": org.id,
            "name": org.name,
            "plan": org.plan,
            "created_at": org.created_at,
        }
        for org in orgs
    ]


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_team(
    name: str,
    plan: PlanType = PlanType.BUSINESS,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> dict:
    """Create a new organisation and add the current user as admin."""
    org = Organisation(name=name, plan=plan)
    db.add(org)
    await db.commit()
    await db.refresh(org)
    # Add membership association
    # Insert into organisation_members table
    await db.execute(
        Organisation.members.through.insert().values(user_id=user.id, organisation_id=org.id, role="admin")
    )
    await db.commit()
    # Refresh user relationship
    await db.refresh(org)
    return {
        "id": org.id,
        "name": org.name,
        "plan": org.plan,
        "created_at": org.created_at,
    }


@router.get("/{team_id}", response_model=dict)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> dict:
    """Get a single team by ID (must be a member)."""
    org = await db.get(Organisation, team_id)
    if not org:
        raise HTTPException(status_code=404, detail="Team not found")
    orgs = getattr(user, "organisations", [])
    if org.id not in [o.id for o in orgs]:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return {
        "id": org.id,
        "name": org.name,
        "plan": org.plan,
        "created_at": org.created_at,
    }


@router.put("/{team_id}", response_model=dict)
async def update_team(
    team_id: int,
    name: str = None,
    plan: PlanType = None,
    db: AsyncSession = Depends(get_db_session),
    user = Depends(get_user),
) -> dict:
    """Update a team (admin only)."""
    org = await db.get(Organisation, team_id)
    if not org:
        raise HTTPException(status_code=404, detail="Team not found")
    # Check admin role
    orgs = getattr(user, "organisations", [])
    membership = next((o for o in orgs if o.id == org.id), None)
    if not membership or getattr(membership, "role", None) != "admin":
        raise HTTPException(status_code=403, detail="Not an admin of this team")
    if name:
        org.name = name
    if plan:
        org.plan = plan
    await db.commit()
    await db.refresh(org)
    return {
        "id": org.id,
        "name": org.name,
        "plan": org.plan,
        "created_at": org.created_at,
    }


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    db: AsyncSession = Depends(get_db_session),
    clerk_user = Depends(get_clerk_user),
):
    """Delete a team (admin only)."""
    org = await db.get(Organisation, team_id)
    if not org:
        raise HTTPException(status_code=404, detail="Team not found")
    # Clerk RBAC: must have 'admin' role
    from app.api.dependencies import require_role
    require_role(clerk_user, "admin")
    await db.delete(org)
    await db.commit()