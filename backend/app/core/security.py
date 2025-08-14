"""Security and authentication utilities.

In a production system this module would integrate with an
authentication provider such as Auth0, Clerk, or a custom OAuth2
implementation. It would verify JSON Web Tokens (JWTs), handle
refresh tokens, enforce role based access control and provide
helpers to extract the currently authenticated user from the
request.

For the purposes of this example implementation we provide a
simple stub that simulates a single authenticated user and
organisation. All API requests are treated as if they originate
from the same user, and no password or token validation is
performed. This is sufficient for demonstrating the core
functionality of receipt extraction, auditing and evaluation but
should be replaced with real authentication in production.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.tables import User, PlanType
from datetime import datetime
import logging
from app.core.config import settings

import os
import httpx
from jose import jwt
import requests

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_API_URL = "https://api.clerk.dev/v1"
CLERK_JWKS_URL = "https://measured-hyena-43.clerk.accounts.dev/.well-known/jwks.json"

# Cache JWKS to avoid repeated network calls
_clerk_jwks = None
def get_clerk_jwks():
    global _clerk_jwks
    if _clerk_jwks is None:
        resp = requests.get(CLERK_JWKS_URL)
        resp.raise_for_status()
        _clerk_jwks = resp.json()
    return _clerk_jwks
auth_scheme = HTTPBearer()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    request: Request = None
) -> User:
    """Get current user from JWT or create dev user in dev mode.

    Adds lightweight debug logging (info level) so we can see which path executed
    when diagnosing mismatched Clerk vs Dev user records.
    """

    if settings.DEV_AUTH_BYPASS:
        logging.getLogger(__name__).info("Auth bypass active; returning Dev User placeholder")
        # Check if dev user exists
        result = await db.execute(
            select(User).where(User.email == "dev@example.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create dev user with a dummy clerk_id
            user = User(
                clerk_id="dev_clerk_id_12345",  # Add a non-null clerk_id
                email="dev@example.com",
                name="Dev User",
                plan=PlanType.FREE
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        
        return user
    

    auth_header = request.headers.get("Authorization") if request else None
    if not auth_header:
        logging.getLogger(__name__).warning("Missing Authorization header while DEV_AUTH_BYPASS disabled")

    # HTTPBearer is an async callable; ensure we await it to obtain credentials
    credentials: HTTPAuthorizationCredentials = await auth_scheme(request)  # type: ignore[arg-type]
    token = credentials.credentials

    # Verify JWT signature and decode using Clerk's public JWKS
    try:
        jwks = get_clerk_jwks()
        payload = jwt.decode(
            token,
            jwks,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            raise HTTPException(status_code=401, detail="Invalid Clerk token: no sub claim")
    except Exception as e:
        logging.getLogger(__name__).warning(f"JWT decode failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid Clerk token: {str(e)}")

    # Fetch Clerk user info
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CLERK_API_URL}/users/{clerk_user_id}", headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"})
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Clerk user not found")
        clerk_user = resp.json()
    email = clerk_user.get("email_addresses", [{}])[0].get("email_address") or clerk_user.get("email_address")
    name = clerk_user.get("first_name", "") + " " + clerk_user.get("last_name", "")
    if not email:
        raise HTTPException(status_code=400, detail="Clerk user missing email")

    # Find or create user in Neon (prefer matching by clerk_id, fallback to email)
    result = await db.execute(User.__table__.select().where(User.clerk_id == clerk_user_id))
    row = result.first()
    if not row:
        result_email = await db.execute(User.__table__.select().where(User.email == email))
        row = result_email.first()
    if row:
        user = User(**row._mapping)
        # Backfill missing clerk_id if somehow null (legacy rows)
        if not getattr(user, "clerk_id", None):
            logging.getLogger(__name__).info("Backfilling missing clerk_id for existing user %s", user.id)
            await db.execute(
                User.__table__.update().where(User.id == user.id).values(clerk_id=clerk_user_id)
            )
            await db.commit()
            user.clerk_id = clerk_user_id
        return user
    new_user = User(clerk_id=clerk_user_id, email=email, name=name.strip() or email, plan=PlanType.PRO)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user