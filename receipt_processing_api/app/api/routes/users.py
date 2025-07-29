"""API route for retrieving the current user profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_user, get_clerk_user
from app.models.schemas import UserRead, UserCreate, UserUpdate
from app.models.tables import User
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db_session


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_current_user(user = Depends(get_clerk_user)) -> UserRead:
    """Return the authenticated user's profile and plan."""
    return UserRead(**user.__dict__)

# Create new user
@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: AsyncSession = Depends(get_db_session)):
    # Check for duplicate Clerk ID
    existing = await db.execute(
        User.__table__.select().where(User.clerk_id == user_in.clerk_id)
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Clerk ID already registered")
    user = User(clerk_id=user_in.clerk_id, email=user_in.email, name=user_in.name, plan=user_in.plan)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserRead.from_orm(user)

# Get user by ID
@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(user_id: int, db: AsyncSession = Depends(get_db_session)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.from_orm(user)

# List users
@router.get("", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(User.__table__.select())
    users = result.fetchall()
    return [UserRead.from_orm(u) for u in users]

# Update user
@router.put("/{user_id}", response_model=UserRead)
async def update_user(user_id: int, user_in: UserUpdate, db: AsyncSession = Depends(get_db_session)):
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

# Delete user
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db_session),
    clerk_user = Depends(get_clerk_user),
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    from app.api.dependencies import require_owner_or_admin
    require_owner_or_admin(clerk_user, user.clerk_id)
    await db.delete(user)
    await db.commit()