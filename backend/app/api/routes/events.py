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

from app.api.dependencies import get_redis_client, get_clerk_user
from app.core.config import settings


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
async def receipts_stream(request: Request, redis=Depends(get_redis_client)):
    """SSE stream of receipt update events for the current user.

    - In production, reads the user from Clerk JWT via get_clerk_user.
    - In development with DEV_AUTH_BYPASS, falls back to user id 1.
    """
    # Determine user id
    user_id: int | None = None
    try:
        # get_clerk_user returns a SimpleNamespace or JWT payload
        payload = get_clerk_user(request)
        # Accept either attribute or dict access patterns
        user_id = getattr(payload, "id", None) or getattr(payload, "user_id", None)  # type: ignore[attr-defined]
        if user_id is None and isinstance(payload, dict):
            user_id = payload.get("id") or payload.get("user_id")  # type: ignore[assignment]
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        if not isinstance(user_id, int):
            # Fall through to dev default
            user_id = None
    except Exception:
        user_id = None

    if user_id is None:
        if settings.DEV_AUTH_BYPASS:
            user_id = 1
        else:
            raise HTTPException(status_code=401, detail="Unauthenticated")

    # Return streaming response
    return StreamingResponse(
        _receipt_event_stream(user_id, redis),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    generator = _receipt_event_stream(user_id=user.id, receipt_id=receipt_id)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
