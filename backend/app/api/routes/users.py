"""API routes for user management.

This router exposes endpoints for retrieving and managing the current user.  It
relies on `app.core.security.get_current_user` to ensure authentication is
consistent across the backend.  When creating users via the API the plan is
defaulted to `FREE` and inputs are sanitised via Pydantic models.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db_session, get_clerk_payload
from app.core.security import get_current_user
from app.models.schemas import UserRead, UserCreate, UserUpdate
from app.models.tables import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_current_user(user: User = Depends(get_current_user)) -> UserRead:
    """Return the authenticated user's profile."""
    return UserRead.from_orm(user)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db_session)) -> UserRead:
    """Create a new user.  The `clerk_id` must be unique."""
    # Check for duplicate Clerk ID
    existing = await db.execute(
        User.__table__.select().where(User.clerk_id == user_in.clerk_id)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Clerk ID already registered")
    # Always default to FREE plan when creating users via this endpoint
    user = User(
        clerk_id=user_in.clerk_id,
        email=user_in.email,
        name=user_in.name,
        plan=user_in.plan,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserRead.from_orm(user)


@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(user_id: int, db: AsyncSession = Depends(get_db_session)) -> UserRead:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.from_orm(user)


@router.get("", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db_session)) -> list[UserRead]:
    result = await db.execute(User.__table__.select())
    users = result.fetchall()
    return [UserRead.from_orm(u) for u in users]


@router.put("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, user_in: UserUpdate, db: AsyncSession = Depends(get_db_session)) -> UserRead:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_in.name:
        user.name = user_in.name
    if user_in.plan:
        user.plan = user_in.plan
    await db.commit()
    await db.refresh(user)
    return UserRead.from_orm(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    payload: dict = Depends(get_clerk_payload),
) -> Response:
    """Delete a user if the caller is the owner or has the `admin` role.

    The caller's Clerk JWT is decoded via `get_clerk_payload`, which provides
    access to the `sub` claim (the caller's Clerk user ID) and roles.  The
    helper `require_owner_or_admin` enforces that only the resource owner or
    administrators can delete a user.
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    from app.api.dependencies import require_owner_or_admin
    require_owner_or_admin(payload, user.clerk_id)
    await db.delete(user)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)