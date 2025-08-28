"""Common dependencies for FastAPI routes.

This module defines shared dependency functions such as database access,
rate‑limiting helpers and authentication helpers.  It has been updated to
delegate Clerk token verification to `app.core.security` so that JWT
validation logic is centralised and consistent.  The JWKS and API URLs are
configured via environment variables.  See `app/core/security.py` for
details.
"""

from __future__ import annotations

import time
from typing import AsyncGenerator, Dict, List, Optional
from types import SimpleNamespace

import requests
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt  # used only for custom verifications if needed

from app.core.database import get_db
# Import both JWT decoder and current-user resolver from security module
from app.core.security import decode_clerk_jwt, get_current_user
from app.models.enums import PlanType
from app.models.tables import User
from app.services.audit_service import AuditService
from app.core.config import settings

try:
    from redis import asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover - fallback if redis asyncio missing
    aioredis = None  # type: ignore


# -----------------------------------------------------------------------------
# Shared resources

_redis_client = None  # type: ignore


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Alias for `get_db` to be imported in routers."""
    async for session in get_db():
        yield session


async def get_redis_client():
    """Return a singleton async Redis client using `REDIS_URL`."""
    global _redis_client
    if _redis_client is None:
        if aioredis is None:
            raise HTTPException(status_code=503, detail="Redis not available for rate limiting")
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


# -----------------------------------------------------------------------------
# Rate limiting helpers

async def enforce_rate_limit(user_id: int, action: str, limit: int, window_seconds: int, cost: int = 1):
    """Fixed-window rate limit per user/action using Redis."""
    client = await get_redis_client()
    now = int(time.time())
    window_id = now // window_seconds
    key = f"rl:{action}:{user_id}:{window_id}"
    # Initialise window and increment atomically
    pipe = client.pipeline()
    pipe.set(key, 0, ex=window_seconds, nx=True)
    pipe.incrby(key, cost)
    try:
        _, count = await pipe.execute()
    except Exception:
        # Fallback: best-effort non-atomic
        try:
            count = await client.incrby(key, cost)
            await client.expire(key, window_seconds)
        except Exception:
            raise HTTPException(status_code=503, detail="Rate limiter unavailable")
    if int(count) > limit:
        ttl = await client.ttl(key)
        headers = {"Retry-After": str(max(1, int(ttl))) if isinstance(ttl, int) and ttl > 0 else "60"}
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers=headers)


def _get_plan_limits(plan: PlanType) -> dict:
    """Return per-plan action limits (requests per minute)."""
    limits = {
        PlanType.FREE: {"upload_per_min": 10, "reprocess_per_min": 5},
        PlanType.PERSONAL: {"upload_per_min": 20, "reprocess_per_min": 10},
        PlanType.PRO: {"upload_per_min": 60, "reprocess_per_min": 30},
        PlanType.BUSINESS: {"upload_per_min": 120, "reprocess_per_min": 60},
        PlanType.ENTERPRISE: {"upload_per_min": 300, "reprocess_per_min": 150},
    }
    return limits.get(plan, limits[PlanType.FREE])


async def enforce_tiered_rate_limit(user: User, action: str, cost: int = 1) -> None:
    """Apply tier-aware per-minute rate limits for a given action."""
    plan_limits = _get_plan_limits(getattr(user, "plan", PlanType.FREE))
    key_map = {"upload": "upload_per_min", "reprocess": "reprocess_per_min"}
    limit_key = key_map.get(action)
    if not limit_key:
        # Unknown action, default to conservative limit
        await enforce_rate_limit(user.id, action, limit=10, window_seconds=60, cost=cost)
        return
    limit = int(plan_limits.get(limit_key, 10))
    await enforce_rate_limit(user.id, action, limit=limit, window_seconds=60, cost=cost)


# -----------------------------------------------------------------------------
# Clerk authentication helpers

def require_role(payload: Dict, required_role: str) -> None:
    """Ensure the user has a specific role claim."""
    roles = payload.get("roles", [])
    if required_role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires {required_role} role")


def require_owner_or_admin(payload: Dict, resource_owner_clerk_id: str) -> None:
    """Ensure the caller is the resource owner or has the `admin` role."""
    clerk_id = payload.get("sub")
    roles = payload.get("roles", [])
    if clerk_id != resource_owner_clerk_id and "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")


def get_clerk_payload(request: Request) -> Dict:
    """Extract and verify the Clerk JWT from the request and return its payload.

    This helper decodes the JWT using the shared logic in `app.core.security`.  It
    checks the `Authorization` header for a `Bearer` token.  Audience and issuer
    verification are applied based on environment configuration.
    """
    if settings.DEV_AUTH_BYPASS:
        # In dev mode we return a fake payload with minimal claims
        return {
            "sub": "user_dev123",
            "email": "dev@example.com",
            "name": "Dev User",
            "roles": ["admin"],
        }
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Clerk JWT")
    token = auth_header.split(" ", 1)[1]
    payload = decode_clerk_jwt(token)
    return payload


async def get_clerk_user(request: Request) -> SimpleNamespace:
    """Return a simple object representing the current Clerk user.

    This dependency decodes the JWT and maps common claims to attributes.  It
    returns a `SimpleNamespace` to mirror the previous behaviour used by the
    `users` router.  For full database user resolution use
    `app.core.security.get_current_user` instead.
    """
    payload = get_clerk_payload(request)
    return SimpleNamespace(
        sub=payload.get("sub"),
        email=payload.get("email"),
        name=payload.get("name"),
        roles=payload.get("roles", []),
    )


async def get_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the current user.  Raises if not authenticated."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    return current_user


async def get_audit_service(db: AsyncSession = Depends(get_db_session)) -> AuditService:
    """Get audit service instance."""
    return AuditService()


# -----------------------------------------------------------------------------
# PDF -> image helper used by ExtractionService
# -----------------------------------------------------------------------------
try:  # Local optional import; PyMuPDF is in requirements but guard defensively
    import fitz  # type: ignore
except Exception:  # pragma: no cover
    fitz = None  # type: ignore

async def process_pdf_to_images(data: bytes, max_pages: int = 5, dpi: int = 144) -> list[bytes]:
    """Convert a PDF byte stream into a list of page images (PNG bytes).

    Only the first ``max_pages`` pages are rendered to avoid huge memory usage.
    Returns an empty list if PDF rendering is unavailable or fails.
    """
    if not data:
        return []
    if fitz is None:  # PyMuPDF not available
        return []
    images: list[bytes] = []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        page_count = min(doc.page_count, max_pages)
        for i in range(page_count):
            page = doc.load_page(i)
            # Use matrix for DPI scaling
            zoom = dpi / 72.0  # base DPI is 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            images.append(pix.tobytes("png"))
        doc.close()
    except Exception:  # pragma: no cover - graceful degradation
        return []
    return images