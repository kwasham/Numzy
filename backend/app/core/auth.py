import os
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import User
from app.core.database import get_db
from app.core.config import settings

security = HTTPBearer()

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    """Get current user from JWT or create dev user in dev mode."""
    
    if settings.DEV_AUTH_BYPASS:
        # In dev mode, bypass auth completely
        result = await db.execute(
            select(User).where(User.email == "dev@example.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create dev user with a dummy clerk_id
            user = User(
                clerk_id="dev_clerk_id_12345",
                email="dev@example.com",
                name="Dev User",
                plan=PlanType.FREE
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        return user
    
    # Production auth flow
    if not credentials:
        raise HTTPException(status_code=401, detail="No credentials provided")
    
    token = credentials.credentials
    # ... rest of your JWT verification code