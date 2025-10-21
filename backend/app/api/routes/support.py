from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.api.dependencies import get_user
from app.core.config import settings
from app.core.security import get_current_user
from sqlalchemy import select
from app.models.tables import SupportThread, SupportMessage, User

router = APIRouter(prefix="/support", tags=["support"]) 

@router.get("/threads")
async def list_support_threads(
    request: Request,
    limit: int = Query(5, ge=1, le=50),
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Support threads list (top messages).

    Uses the new support tables when available; falls back to synthetic data when empty.
    """
    # Enforce authentication outside dev-bypass mode
    if not settings.DEV_AUTH_BYPASS:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            await get_current_user(request=request, db=db)
        elif token:
            # Dev-only shortcut: accept a simple test token if configured
            if settings.TEST_USER_JWT and token == settings.TEST_USER_JWT:
                # Ensure dev user exists; skip Clerk network
                result = await db.execute(select(User).where(User.email == "dev@example.com"))
                user = result.scalar_one_or_none()
                if user is None:
                    from app.models.enums import PlanType
                    user = User(
                        clerk_id="dev_clerk_id_12345",
                        email="dev@example.com",
                        name="Dev User",
                        plan=PlanType.FREE,
                    )
                    db.add(user)
                    await db.commit()
                    await db.refresh(user)
            else:
                # Verify token like events endpoint (ensure local user)
                from app.core.security import decode_clerk_jwt, CLERK_SECRET_KEY, CLERK_API_URL
                import httpx
                payload = decode_clerk_jwt(token)
                clerk_user_id = payload.get("sub")
                if not clerk_user_id:
                    raise HTTPException(status_code=401, detail="Invalid Clerk token: no sub claim")
                from sqlalchemy import select
                result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
                user = result.scalar_one_or_none()
                if user is None:
                    if not CLERK_SECRET_KEY:
                        raise HTTPException(status_code=500, detail="Clerk secret key not configured")
                    async with httpx.AsyncClient(timeout=5) as client:
                        resp = await client.get(
                            f"{CLERK_API_URL}/users/{clerk_user_id}",
                            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
                        )
                    if resp.status_code != 200:
                        raise HTTPException(status_code=401, detail="Clerk user not found")
                    clerk_user = resp.json()
                    email = (
                        clerk_user.get("email_addresses", [{}])[0].get("email_address")
                        or clerk_user.get("email_address")
                    )
                    first = clerk_user.get("first_name", "")
                    last = clerk_user.get("last_name", "")
                    name = f"{first} {last}".strip() or email
                    if not email:
                        raise HTTPException(status_code=400, detail="Clerk user missing email")
                    # Backfill by email if needed
                    result = await db.execute(select(User).where(User.email == email))
                    user = result.scalar_one_or_none()
                    if user:
                        if not getattr(user, "clerk_id", None):
                            user.clerk_id = clerk_user_id  # type: ignore[attr-defined]
                            db.add(user)
                            await db.commit()
                            await db.refresh(user)
                    else:
                        from app.models.enums import PlanType
                        user = User(email=email, name=name, clerk_id=clerk_user_id, plan=PlanType.FREE)
                        db.add(user)
                        await db.commit()
                        await db.refresh(user)
        else:
            raise HTTPException(status_code=401, detail="Missing auth token")

    # Prefer real support data
    res = await db.execute(
        select(SupportThread).order_by(SupportThread.created_at.desc()).limit(limit)
    )
    threads_rows = res.scalars().all()
    threads = []
    if threads_rows:
        for t in threads_rows:
            # Fetch latest message for each thread
            mr = await db.execute(
                select(SupportMessage).where(SupportMessage.thread_id == t.id).order_by(SupportMessage.created_at.desc()).limit(1)
            )
            last = mr.scalars().first()
            # Resolve author (best effort)
            author = None
            if t.author_id:
                ar = await db.execute(select(User).where(User.id == t.author_id))
                author = ar.scalars().first()
            threads.append({
                "id": str(t.id),
                "content": (last.content if last else (t.subject or "")) or "",
                "author": {
                    "name": getattr(author, "name", "User"),
                    "avatar": "/assets/avatar-1.png",
                    "status": "offline",
                },
                "created_at": (last.created_at if last else t.created_at),
            })
    # Fallback if no support threads exist yet
    if not threads:
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        threads = [
            {
                "id": "MSG-001",
                "content": "Hello, we spoke earlier on the phone",
                "author": {"name": "Alcides Antonio", "avatar": "/assets/avatar-10.png", "status": "online"},
                "created_at": now - timedelta(minutes=2),
            },
            {
                "id": "MSG-002",
                "content": "Is the job still available?",
                "author": {"name": "Marcus Finn", "avatar": "/assets/avatar-9.png", "status": "offline"},
                "created_at": now - timedelta(minutes=56),
            },
            {
                "id": "MSG-003",
                "content": "What is a screening task? I'd like to",
                "author": {"name": "Carson Darrin", "avatar": "/assets/avatar-3.png", "status": "online"},
                "created_at": now - timedelta(hours=3, minutes=23),
            },
        ]
    return threads
