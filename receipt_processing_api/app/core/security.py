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

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.tables import User, PlanType
from datetime import datetime
from app.models.enums import PlanType

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
    credentials=Depends(auth_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Clerk JWT, fetch Clerk user, and ensure user exists in Neon DB."""
    # DEV AUTH BYPASS: If enabled, ensure a dev user exists in the DB and return it
    if os.getenv("DEV_AUTH_BYPASS", "false").lower() == "true":
        dev_email = "dev@example.com"
        result = await db.execute(User.__table__.select().where(User.email == dev_email))
        row = result.first()
        if row:
            user = User(**row._mapping)
            return user
        # Create the dev user if not present
        new_user = User(
            email=dev_email,
            name="Dev User",
            plan=PlanType.FREE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user
    

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

    # Find or create user in Neon
    result = await db.execute(User.__table__.select().where(User.email == email))
    row = result.first()
    if row:
        user = User(**row._mapping)
        return user
    new_user = User(email=email, name=name.strip() or email, plan=PlanType.PRO)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user