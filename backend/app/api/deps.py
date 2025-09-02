from fastapi import Header, Query, BackgroundTasks
from typing import Any

async def user_with_optional_token(
    authorization: str | None = Header(None),
    token: str | None = Query(None),
    background_tasks: BackgroundTasks | None = None,
) -> dict[str, Any] | None:
    """Enhanced auth dependency with better dev fallback."""
    from app.core.config import settings
    from app.utils.auth import decode_clerk_jwt
    import logging

    logger = logging.getLogger(__name__)

    # Development bypass
    if settings.DEV_AUTH_BYPASS:
        logger.info("[auth] DEV_AUTH_BYPASS active, returning dev user")
        return {"sub": "dev_user", "email": "dev@example.com"}
    
    # Try Authorization header first
    auth_token = None
    if authorization and authorization.startswith("Bearer "):
        auth_token = authorization.replace("Bearer ", "")
    elif token:
        auth_token = token
    
    if not auth_token:
        # In development with no token, return dev user instead of None
        if settings.DEBUG:
            logger.info("[auth] No token in dev mode, using fallback user")
            return {"sub": "dev_user", "email": "dev@example.com"}
        return None
    
    try:
        # Attempt to decode the token
        user_info = decode_clerk_jwt(auth_token)
        if user_info:
            return user_info
    except Exception as e:
        logger.warning(f"[auth] Token decode failed: {e}")
        # In development, fallback to dev user on decode failure
        if settings.DEBUG:
            logger.info("[auth] Token decode failed in dev, using fallback user")
            return {"sub": "dev_user", "email": "dev@example.com"}
    
    return None