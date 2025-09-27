"""Backfill script for monthly_receipt_count.

Usage (inside backend container / virtualenv):

  python -m app.scripts.backfill_monthly_usage

Logic:
  - For each user, if monthly_receipt_count is NULL, compute COUNT(*) of receipts
    created in the current UTC calendar month and store it.
  - Does NOT overwrite existing non-null counters.
  - Emits basic progress logging; safe to re-run (idempotent for already-set users).

Observability: emits sentry metrics (best-effort) for counts processed.
"""
from __future__ import annotations

import asyncio
import datetime as dt
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.tables import User, Receipt
from app.core.observability import sentry_metric_inc, sentry_breadcrumb


async def _backfill(session: AsyncSession) -> None:
    now = dt.datetime.utcnow()
    start = dt.datetime(now.year, now.month, 1, tzinfo=dt.timezone.utc)
    if now.month == 12:
        end = dt.datetime(now.year + 1, 1, 1, tzinfo=dt.timezone.utc)
    else:
        end = dt.datetime(now.year, now.month + 1, 1, tzinfo=dt.timezone.utc)

    result = await session.execute(select(User).order_by(User.id))
    users = result.scalars().all()
    updated = 0
    skipped = 0
    for u in users:
        if u.monthly_receipt_count is not None:
            skipped += 1
            continue
        # COUNT receipts in current month
        q = select(func.count(Receipt.id)).where(
            Receipt.owner_id == u.id,
            Receipt.created_at >= start,
            Receipt.created_at < end,
        )
        r = await session.execute(q)
        count = int(r.scalar() or 0)
        u.monthly_receipt_count = count
        session.add(u)
        updated += 1
        if updated % 50 == 0:
            print(f"Progress: updated {updated} users (skipped {skipped})")
    await session.commit()
    print(f"Backfill complete: updated={updated} skipped={skipped} total={len(users)}")
    try:
        sentry_metric_inc("backfill.monthly_usage.updated", value=updated)
        sentry_metric_inc("backfill.monthly_usage.skipped", value=skipped)
        sentry_breadcrumb(
            category="backfill",
            message="monthly_usage.complete",
            data={"updated": updated, "skipped": skipped},
        )
    except Exception:
        pass


async def main():
    async with async_session_factory() as session:  # type: ignore
        await _backfill(session)


if __name__ == "__main__":
    asyncio.run(main())
