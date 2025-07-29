
"""Common dependencies for FastAPI routes."""

from __future__ import annotations

from typing import AsyncGenerator, List, Optional

from fastapi import Depends, HTTPException


from app.core.database import get_db
from app.core.security import get_current_user
from app.models.tables import User
from app.models.enums import PlanType
import datetime


async def get_db_session() -> AsyncGenerator:
    """Alias for ``get_db`` to be imported in routers."""
    async for session in get_db():
        yield session


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
import requests
from fastapi import Depends, HTTPException, status, Request
from jose import jwt, JWTError
from typing import Dict

# Clerk public JWKS endpoint
CLERK_JWKS_URL = "https://clerk.dev/.well-known/jwks.json"

def get_clerk_public_keys() -> Dict:
    resp = requests.get(CLERK_JWKS_URL)
    resp.raise_for_status()
    return resp.json()

def get_clerk_user(request: Request) -> Dict:
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