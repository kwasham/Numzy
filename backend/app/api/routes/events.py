from __future__ import annotations

"""Server-Sent Events (SSE) endpoints.

Exposes a receipt updates stream backed by Redis pub/sub. The stream
subscribes to the per-user channel used by background tasks:
``receipts:user:{user_id}``.

In development with DEV_AUTH_BYPASS=true, the user id defaults to 1
if no auth context is available.
"""

import asyncio
import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import StreamingResponse

from app.api.dependencies import get_redis_client, get_user, get_db_session
from app.models.tables import User
from app.core.config import settings
from app.core.security import decode_clerk_jwt, CLERK_SECRET_KEY, CLERK_API_URL
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import httpx


router = APIRouter(prefix="/events", tags=["events"])


async def _receipt_event_stream(user_id: int, redis_client) -> AsyncIterator[bytes]:
    """Yield events from Redis pub/sub as SSE frames."""
    pubsub = redis_client.pubsub()
    channel = f"receipts:user:{user_id}"
    await pubsub.subscribe(channel)
    try:
        # Initial comment to confirm connection
        yield b": connected\n\n"
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
            if message and message.get("type") == "message":
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="ignore")
                # Validate JSON or wrap as JSON string
                try:
                    json.loads(data)  # ensure it's JSON
                    payload = data
                except Exception:
                    payload = json.dumps({"raw": data})
                yield f"event: receipt_update\ndata: {payload}\n\n".encode("utf-8")
            else:
                # Keep-alive comment (ignored by browsers) every ~15s
                yield b": keep-alive\n\n"
                await asyncio.sleep(15)
    finally:
        try:
            await pubsub.unsubscribe(channel)
        finally:
            await pubsub.close()


@router.get("/receipts/stream")
async def receipts_stream(
    request: Request,
    token: str | None = None,
    redis=Depends(get_redis_client),
    db: AsyncSession = Depends(get_db_session),
):
    """SSE stream of receipt update events for the current (DB) user.

    Problem: Browser `EventSource` cannot attach custom `Authorization` headers so our
    previous dependency on `get_user` (which requires a Bearer token header) caused
    403 responses when the header was absent.

    Solution: Accept an optional `token` query parameter (`?token=`) carrying the Clerk
    JWT. If the Authorization header is present we still use the standard dependency
    path for consistency (by calling `get_user`). Otherwise we decode the provided
    token, resolve (or create) the local user record and proceed. In dev bypass mode
    we fall back to / seed the dev user without requiring a token.

    Security notes:
    - Query-string tokens may be logged by intermediaries; this is acceptable for
      short‑term development but should be replaced by an ephemeral signed SSE token
      (handshake endpoint) before production hardening.
    - Tokens are still fully verified (signature & claims) via existing
      `decode_clerk_jwt` logic.
    """

    # Fast path: if header present let the existing auth flow work (reuse get_user)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # Delegate to the existing dependency logic
        user: User = await get_user()  # type: ignore
    else:
        # Dev bypass mode: synthesise / fetch the dev user
        if settings.DEV_AUTH_BYPASS:
            result = await db.execute(select(User).where(User.email == "dev@example.com"))
            user = result.scalar_one_or_none()
            if user is None:
                from app.models.enums import PlanType  # local import to avoid cycle

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
            if not token:
                raise HTTPException(status_code=401, detail="Missing auth token")
            # Decode and verify Clerk JWT
            payload = decode_clerk_jwt(token)
            clerk_user_id = payload.get("sub")
            if not clerk_user_id:
                raise HTTPException(status_code=401, detail="Invalid Clerk token: no sub claim")
            # Lookup existing by clerk_id
            result = await db.execute(select(User).where(User.clerk_id == clerk_user_id))
            user = result.scalar_one_or_none()
            if user is None:
                # Optionally fetch user details from Clerk to populate email/name
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
                # Try existing by email
                result = await db.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                if user:
                    if not getattr(user, "clerk_id", None):
                        user.clerk_id = clerk_user_id  # type: ignore[attr-defined]
                        db.add(user)
                        await db.commit()
                        await db.refresh(user)
                else:
                    from app.models.enums import PlanType  # local import

                    user = User(email=email, name=name, clerk_id=clerk_user_id, plan=PlanType.FREE)
                    db.add(user)
                    await db.commit()
                    await db.refresh(user)

    return StreamingResponse(
        _receipt_event_stream(user.id, redis),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# Backwards compatibility route (legacy path /receipts/events) used by older frontend builds.
# It simply delegates to the new /events/receipts/stream implementation.
@router.get("/legacy-receipts")
async def legacy_receipts_redirect(
    request: Request,
    redis=Depends(get_redis_client),
    user: User = Depends(get_user),
):
    return await receipts_stream(request, redis, user)  # type: ignore[arg-type]
