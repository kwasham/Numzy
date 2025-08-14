"""Common dependencies for FastAPI routes."""

from __future__ import annotations
import requests
from typing import AsyncGenerator, List, Optional
import time

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.audit_service import AuditService

from jose import jwt, JWTError
from typing import Dict
from types import SimpleNamespace

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.tables import User
from app.models.enums import PlanType
from app.core.config import settings

# Async Redis client (shared)
try:
    from redis import asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover - fallback if redis asyncio missing
    aioredis = None  # type: ignore

_redis_client = None  # type: ignore

async def get_redis_client():
    """Return a singleton async Redis client using REDIS_URL."""
    global _redis_client
    if _redis_client is None:
        if aioredis is None:
            raise HTTPException(status_code=503, detail="Redis not available for rate limiting")
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def enforce_rate_limit(user_id: int, action: str, limit: int, window_seconds: int, cost: int = 1):
    """Fixed-window rate limit per user/action using Redis.

    - Increments a counter by `cost` within the current window.
    - Sets window TTL on first write.
    - Raises 429 if the limit would be exceeded.
    """
    client = await get_redis_client()
    now = int(time.time())
    window_id = now // window_seconds
    key = f"rl:{action}:{user_id}:{window_id}"

    # Initialize window and increment atomically
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
        # Compute remaining time in window for Retry-After
        ttl = await client.ttl(key)
        headers = {"Retry-After": str(max(1, int(ttl))) if isinstance(ttl, int) and ttl > 0 else "60"}
        raise HTTPException(status_code=429, detail="Rate limit exceeded", headers=headers)


def _get_plan_limits(plan: PlanType) -> dict:
    """Return per-plan action limits (requests per minute).

    Defaults to FREE if plan is unknown.
    """
    limits = {
        PlanType.FREE: {"upload_per_min": 10, "reprocess_per_min": 5},
        PlanType.PRO: {"upload_per_min": 60, "reprocess_per_min": 30},
        PlanType.BUSINESS: {"upload_per_min": 120, "reprocess_per_min": 60},
        PlanType.ENTERPRISE: {"upload_per_min": 300, "reprocess_per_min": 150},
    }
    return limits.get(plan, limits[PlanType.FREE])


async def enforce_tiered_rate_limit(user: User, action: str, cost: int = 1) -> None:
    """Apply tier-aware per-minute rate limits for a given action.

    Actions supported: "upload", "reprocess".
    """
    plan_limits = _get_plan_limits(getattr(user, "plan", PlanType.FREE))
    key_map = {"upload": "upload_per_min", "reprocess": "reprocess_per_min"}
    limit_key = key_map.get(action)
    if not limit_key:
        # Unknown action, default to conservative limit
        await enforce_rate_limit(user.id, action, limit=10, window_seconds=60, cost=cost)
        return
    limit = int(plan_limits.get(limit_key, 10))
    await enforce_rate_limit(user.id, action, limit=limit, window_seconds=60, cost=cost)



# Clerk public JWKS endpoint
CLERK_JWKS_URL = "https://clerk.dev/.well-known/jwks.json"


async def get_db_session() -> AsyncGenerator:
    """Alias for ``get_db`` to be imported in routers."""
    async for session in get_db():
        yield session
        

async def get_audit_service(
    db: AsyncSession = Depends(get_db_session),
) -> AuditService:
    """Get audit service instance."""
    return AuditService()  # Don't pass db to constructor


async def get_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the current user. Raises if not authenticated."""
    if not current_user:
        
        raise HTTPException(status_code=401, detail="Unauthenticated")
    return current_user



async def process_pdf_to_images(data: bytes) -> List[bytes]:
    """Convert PDF bytes into a list of JPEG images.

    This helper uses PyMuPDF (fitz) if available. If the library is
    missing or an error occurs it returns an empty list and relies
    on the caller to handle the error condition.
    """
    try:
        import fitz  # type: ignore
    except ImportError:
        return []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        images: List[bytes] = []
        for page in doc:
            pix = page.get_pixmap()
            images.append(pix.tobytes("png"))
        return images
    except Exception:
        return []
    

# RBAC and owner check helpers
def require_role(payload, required_role: str):
    roles = payload.get("roles", [])
    if required_role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires {required_role} role")

def require_owner_or_admin(payload, resource_owner_clerk_id: str):
    clerk_id = payload.get("sub")
    roles = payload.get("roles", [])
    if clerk_id != resource_owner_clerk_id and "admin" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")



def get_clerk_public_keys() -> Dict:
    resp = requests.get(CLERK_JWKS_URL)
    resp.raise_for_status()
    return resp.json()

def get_clerk_user(request: Request):
    # Check if we're in dev mode with auth bypass
    if settings.DEV_AUTH_BYPASS:
        # Return an object with attributes instead of a dict
        return SimpleNamespace(
            id=1,  # Use numeric ID for database
            sub="user_dev123", 
            email="dev@example.com",
            name="Dev User"
        )
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Clerk JWT")
    token = auth_header.split(" ", 1)[1]
    jwks = get_clerk_public_keys()
    try:
        unverified_header = jwt.get_unverified_header(token)
        key = next((k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]), None)
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Clerk JWT")
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
        payload = jwt.decode(token, public_key, algorithms=[unverified_header["alg"]], audience=None, options={"verify_aud": False})
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Clerk JWT")
    return payload