"""Security and authentication utilities for Clerk integration.

This module provides functions to verify Clerk-issued JWTs, retrieve Clerk users via
the Clerk REST API and map them to local database users.  It follows best
practices by parameterising the Clerk API endpoints and verifying the `aud`
and `iss` claims on incoming tokens.  All configuration values can be set via
environment variables.  For example, set `CLERK_JWKS_URL` to your instance’s
`https://<your-clerk-domain>/.well-known/jwks.json` and `CLERK_API_URL` to
`https://api.clerk.com/v1` or `https://api.clerk.dev/v1` depending on the
environment.  See the README for more details.
"""

from __future__ import annotations

import os
from typing import Optional, Dict

import httpx  # type: ignore
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from jose import jwt
import requests
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.config import settings
from app.models.enums import PlanType
from app.models.tables import User

# -----------------------------------------------------------------------------
# Configuration
#
# Clerk configuration values are read from environment variables with sensible
# defaults.  These can be overridden per-environment without changing code.  In
# production you should set these explicitly.

CLERK_SECRET_KEY: Optional[str] = os.getenv("CLERK_SECRET_KEY")

# Base URL for Clerk's REST API.  Defaults to Clerk's production endpoint.
CLERK_API_URL: str = os.getenv("CLERK_API_URL", "https://api.clerk.com/v1")

# JWKS endpoint used for verifying JWT signatures.  You MUST set this to your
# Clerk instance’s JWKS URL (e.g. `https://<frontend-api>/.well-known/jwks.json`).
CLERK_JWKS_URL: str = os.getenv("CLERK_JWKS_URL", "")

# Audience and issuer values used when decoding JWTs.  Set these to
# `CLERK_JWT_AUDIENCE` and `CLERK_JWT_ISSUER` in your environment for extra
# security.  If unset, audience/issuer verification is skipped.
CLERK_JWT_AUDIENCE: Optional[str] = os.getenv("CLERK_JWT_AUDIENCE")
CLERK_JWT_ISSUER: Optional[str] = os.getenv("CLERK_JWT_ISSUER")

auth_scheme = HTTPBearer()

# JWKS cache.  In production consider TTL and periodic refresh.
_clerk_jwks: Optional[Dict] = None


def get_clerk_jwks() -> Dict:
    """Fetch and cache the JWKS used to verify Clerk tokens.

    This function retrieves the JWKS from the configured `CLERK_JWKS_URL`.  The
    result is cached in memory to avoid unnecessary network calls.  If the
    endpoint is unreachable or returns an invalid payload, an HTTP 500
    exception is raised.
    """
    global _clerk_jwks
    if _clerk_jwks is not None:
        return _clerk_jwks
    if not CLERK_JWKS_URL:
        raise RuntimeError(
            "CLERK_JWKS_URL is not configured.  Set it to your Clerk instance's JWKS endpoint."
        )
    try:
        resp = requests.get(CLERK_JWKS_URL, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch JWKS: {exc}") from exc
    # basic shape check
    if not isinstance(data, dict) or "keys" not in data:
        raise HTTPException(status_code=500, detail="Invalid JWKS payload from Clerk")
    _clerk_jwks = data
    return data


def decode_clerk_jwt(token: str) -> Dict:
    """Decode and verify a Clerk JWT.

    The JWT is verified against the JWKS retrieved from the configured
    `CLERK_JWKS_URL`.  If `CLERK_JWT_AUDIENCE` and/or `CLERK_JWT_ISSUER` are set,
    the corresponding claims are validated.  Otherwise, audience/issuer
    verification is disabled.

    Returns:
        The decoded JWT payload as a dictionary.

    Raises:
        HTTPException: If the token is malformed or invalid.
    """
    # Obtain unverified header to find the key ID
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token header: {exc}") from exc
    kid = header.get("kid")
    if not kid:
        raise HTTPException(status_code=401, detail="Invalid Clerk token: missing kid header")
    jwks = get_clerk_jwks()
    key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
    if not key:
        # Clear cache and retry once (rotation scenario)
        global _clerk_jwks
        _clerk_jwks = None
        jwks = get_clerk_jwks()
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(status_code=401, detail="Unknown signing key (kid) for Clerk token")
    try:
        # Build decode parameters.  Only verify audience/issuer when configured.
        decode_kwargs: Dict = {
            "algorithms": ["RS256"],
            "options": {},
        }
        if CLERK_JWT_AUDIENCE:
            decode_kwargs["audience"] = CLERK_JWT_AUDIENCE
        else:
            # Disable audience verification explicitly when no audience provided.
            decode_kwargs.setdefault("options", {})["verify_aud"] = False
        if CLERK_JWT_ISSUER:
            decode_kwargs["issuer"] = CLERK_JWT_ISSUER
        payload = jwt.decode(token, key, **decode_kwargs)
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid Clerk token: {exc}") from exc


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    request: Request | None = None,
) -> User:
    """Resolve the current authenticated user.

    In development mode (`DEV_AUTH_BYPASS`), a placeholder user is returned or
    created.  Otherwise, the function extracts the Bearer token from the
    `Authorization` header, verifies it using Clerk's JWKS, and fetches user
    information from Clerk's REST API.  The corresponding local user is
    retrieved or created.
    """
    # Dev-mode bypass: short-circuit authentication for local testing
    if settings.DEV_AUTH_BYPASS:
        # Look up or create a dev user with a stable clerk_id to satisfy DB
        result = await db.execute(select(User).where(User.email == "dev@example.com"))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                clerk_id="dev_clerk_id_12345",
                email="dev@example.com",
                name="Dev User",
                plan=PlanType.FREE,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user

    # Extract Bearer token via FastAPI's HTTPBearer security scheme
    credentials = await auth_scheme(request)
    token = credentials.credentials
    # Verify token signature and claims
    payload = decode_clerk_jwt(token)
    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Invalid Clerk token: no sub claim")
    if not CLERK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Clerk secret key not configured")
    # Fetch user details from Clerk's API to verify the user exists and is not
    # disabled.  Use AsyncClient for non-blocking I/O.
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.get(
            f"{CLERK_API_URL}/users/{clerk_user_id}",
            headers={"Authorization": f"Bearer {CLERK_SECRET_KEY}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Clerk user not found")
        clerk_user = resp.json()
    # Extract email and name
    email = (
        clerk_user.get("email_addresses", [{}])[0].get("email_address")
        or clerk_user.get("email_address")
    )
    first = clerk_user.get("first_name", "")
    last = clerk_user.get("last_name", "")
    name = f"{first} {last}".strip() or email
    if not email:
        raise HTTPException(status_code=400, detail="Clerk user missing email")
    # Look up existing user by clerk_id or email
    result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
    user = result.scalar_one_or_none()
    if not user:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
    if user:
        # If user exists but has no clerk_id, backfill it
        if not getattr(user, "clerk_id", None):
            user.clerk_id = clerk_user_id  # type: ignore[attr-defined]
            db.add(user)
            await db.commit()
            await db.refresh(user)
        return user
    # Create new user: default to FREE plan (do not auto-provision paid plans)
    new_user = User(email=email, name=name, plan=PlanType.FREE, clerk_id=clerk_user_id)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user