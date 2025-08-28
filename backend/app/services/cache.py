"""Lightweight Redis cache utilities for short-lived API response caching.

Usage guidelines:
- Only cache non-sensitive, per-user scoping (always namespace keys with user id).
- Keep TTLs short (<= 10s) to preserve freshness for rapidly changing statuses.
- Invalidate on mutations (upload, reprocess, update, background completion if practical).
"""
from __future__ import annotations

import json
import asyncio
from typing import Any, Optional, Iterable

try:
    from redis import asyncio as aioredis  # redis>=5
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore

from app.core.config import settings

_redis_client = None
_lock = asyncio.Lock()


async def get_redis():
    """Return a singleton async Redis client or None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    async with _lock:
        if _redis_client is not None:
            return _redis_client
        if aioredis is None:
            return None
        try:
            _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:  # pragma: no cover
            _redis_client = None
    return _redis_client


async def cache_get_json(key: str) -> Optional[Any]:
    client = await get_redis()
    if not client:
        return None
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


async def cache_set_json(key: str, value: Any, ttl: int) -> None:
    client = await get_redis()
    if not client:
        return
    try:
        await client.set(key, json.dumps(value), ex=ttl)
    except Exception:
        pass


async def cache_delete(key: str) -> None:
    client = await get_redis()
    if not client:
        return
    try:
        await client.delete(key)
    except Exception:
        pass


async def cache_delete_pattern(pattern: str) -> None:
    """Best-effort pattern deletion (SCAN + DEL). Avoid for hot paths."""
    client = await get_redis()
    if not client:
        return
    try:
        # Use scan_iter to avoid blocking Redis
        async for key in client.scan_iter(pattern):  # type: ignore[attr-defined]
            try:
                await client.delete(key)
            except Exception:
                pass
    except Exception:
        pass


def summary_cache_key(user_id: int, limit: int, offset: int) -> str:
    return f"receipts:summary:{user_id}:{limit}:{offset}"


def detail_cache_key(user_id: int, receipt_id: int) -> str:
    return f"receipts:detail:{user_id}:{receipt_id}"


async def invalidate_receipts_summary(user_id: int):
    await cache_delete_pattern(f"receipts:summary:{user_id}:*")


async def invalidate_receipt_detail(user_id: int, receipt_id: int):
    await cache_delete(detail_cache_key(user_id, receipt_id))
