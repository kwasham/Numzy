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
from fastapi.security import HTTPBearer

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.tables import User
from datetime import datetime
from app.models.enums import PlanType
from app.core.config import settings

import os
import httpx
from jose import jwt
import requests

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_API_URL = "https://api.clerk.dev/v1"
CLERK_JWKS_URL = "https://measured-hyena-43.clerk.accounts.dev/.well-known/jwks.json"

# Cache JWKS (in‑memory). In production consider TTL + background refresh.
_clerk_jwks: dict | None = None

def get_clerk_jwks() -> dict:
    global _clerk_jwks
    if _clerk_jwks is None:
        resp = requests.get(CLERK_JWKS_URL, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        # basic shape check
        if not isinstance(data, dict) or "keys" not in data:
            raise RuntimeError("Invalid JWKS payload from Clerk")
        _clerk_jwks = data
    return _clerk_jwks

def decode_clerk_jwt(token: str) -> dict:
    """Decode and verify a Clerk JWT using JWKS.

    We select the key with matching `kid` from the JWKS and let python-jose
    verify signature. Audience verification is disabled (adjust as needed).
    """
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=401, detail=f"Invalid token header: {exc}")
    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Invalid Clerk token: missing kid header")
    jwks = get_clerk_jwks()
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        # Invalidate cache & retry once (rotation scenario)
        global _clerk_jwks
        _clerk_jwks = None
        jwks = get_clerk_jwks()
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Unknown signing key (kid) for Clerk token")
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Clerk token: {exc}")
auth_scheme = HTTPBearer()


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    request: Request = None
) -> User:
    """Get current user from JWT or create dev user in dev mode."""
    
    if settings.DEV_AUTH_BYPASS:
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
    

    # FastAPI's HTTPBearer __call__ is async; ensure we await it.
    credentials = await auth_scheme(request)

    token = credentials.credentials

    # Verify JWT signature and decode using Clerk's public JWKS
    payload = decode_clerk_jwt(token)
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Invalid Clerk token: no sub claim")

    if not CLERK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Clerk secret key not configured")

    # Mandatory Clerk API lookup
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

    # Find or create user (prefer lookup by clerk_id first, then email fallback)
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
    if user:
        # Backfill missing clerk_id if needed
        if not getattr(user, 'clerk_id', None):
            user.clerk_id = clerk_user_id  # type: ignore
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user
    new_user = User(email=email, name=name, plan=PlanType.PRO, clerk_id=clerk_user_id)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user