"""Seed demo data for the dashboard in development.

Creates:
- A dev user if missing
- Recent receipts (last 24h) and monthly receipts for usage chart
- A few events
- A few support threads and messages

Idempotent-ish: avoids creating duplicate data on repeated runs by checking counts.
"""
from __future__ import annotations

import asyncio
import datetime as dt
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal, init_db
from app.models.tables import (
    User,
    Receipt,
    Event,
    SupportThread,
    SupportMessage,
    Evaluation,
    EvaluationItem,
)
from app.models.enums import PlanType, ReceiptStatus


async def ensure_dev_user(db: AsyncSession) -> User:
    res = await db.execute(select(User).where(User.email == "dev@example.com"))
    user = res.scalars().first()
    if user:
        return user
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


async def seed_receipts(db: AsyncSession, user: User) -> None:
    # If we already have > 5 receipts in last 30 days, skip
    recent_cutoff = dt.datetime.utcnow() - dt.timedelta(days=30)
    count = (await db.execute(select(Receipt).where(Receipt.created_at >= recent_cutoff))).scalars().all()
    if len(count) >= 5:
        return

    # Create 3 receipts in last 24h (2 completed, 1 processing/open audit)
    now = dt.datetime.utcnow()
    rows: list[Receipt] = []
    rows.append(
        Receipt(
            owner_id=user.id,
            file_path="s3://demo/receipt-1.jpg",
            filename="receipt-1.jpg",
            status=ReceiptStatus.COMPLETED,
            audit_progress=100,
            extraction_progress=100,
            created_at=now - dt.timedelta(hours=2),
        )
    )
    rows.append(
        Receipt(
            owner_id=user.id,
            file_path="s3://demo/receipt-2.jpg",
            filename="receipt-2.jpg",
            status=ReceiptStatus.COMPLETED,
            audit_progress=30,
            extraction_progress=100,
            created_at=now - dt.timedelta(hours=6),
        )
    )
    rows.append(
        Receipt(
            owner_id=user.id,
            file_path="s3://demo/receipt-3.jpg",
            filename="receipt-3.jpg",
            status=ReceiptStatus.PROCESSING,
            audit_progress=0,
            extraction_progress=60,
            created_at=now - dt.timedelta(hours=20),
        )
    )
    # Create a few receipts one per prior months to feed usage chart
    for m in range(1, 6):
        rows.append(
            Receipt(
                owner_id=user.id,
                file_path=f"s3://demo/hist-{m}.jpg",
                filename=f"hist-{m}.jpg",
                status=ReceiptStatus.COMPLETED,
                audit_progress=100,
                extraction_progress=100,
                created_at=(now - dt.timedelta(days=30 * m)),
            )
        )
    db.add_all(rows)
    await db.commit()


async def seed_events(db: AsyncSession) -> None:
    # If events already present, skip
    existing = (await db.execute(select(Event).limit(1))).scalars().first()
    if existing:
        return
    now = dt.datetime.utcnow()
    evts = [
        Event(type="info", title="Ingestion pipeline healthy", description="All workers responding", created_at=now - dt.timedelta(minutes=5)),
        Event(type="receipt", title="Receipt processed", description="receipt-1.jpg", created_at=now - dt.timedelta(hours=1)),
        Event(type="audit", title="Audit flagged", description="Threshold exceeded on amount", created_at=now - dt.timedelta(hours=3)),
        Event(type="info", title="Worker scaled", description="+1 Dramatiq worker", created_at=now - dt.timedelta(days=1)),
    ]
    db.add_all(evts)
    await db.commit()


async def seed_support(db: AsyncSession, user: User) -> None:
    # If threads exist, skip
    existing = (await db.execute(select(SupportThread).limit(1))).scalars().first()
    if existing:
        return
    t1 = SupportThread(subject="How do I export invoices?", author_id=user.id)
    t2 = SupportThread(subject="Upload limits on Personal plan", author_id=user.id)
    db.add_all([t1, t2])
    await db.flush()
    m1 = SupportMessage(thread_id=t1.id, author_id=user.id, content="Hello! I'd like to export last month's invoices.")
    m2 = SupportMessage(thread_id=t2.id, author_id=user.id, content="Is there a way to increase my monthly limit?")
    db.add_all([m1, m2])
    await db.commit()


async def seed_evaluations(db: AsyncSession, user: User) -> None:
    """Create a small evaluation with items spread over last 14 days.

    This drives the avgAccuracy7d and avgAccuracyPrev7d metrics with real data.
    Idempotent-ish: if there are any evaluation_items within the last 14 days, skip.
    """
    now = dt.datetime.utcnow()
    cutoff = now - dt.timedelta(days=14)
    existing = (
        await db.execute(
            select(EvaluationItem).where(EvaluationItem.created_at >= cutoff).limit(1)
        )
    ).scalars().first()
    if existing:
        return

    eval_run = Evaluation(owner_id=user.id, model_name="demo-model", summary_metrics={})
    db.add(eval_run)
    await db.flush()

    items: list[EvaluationItem] = []
    # Recent 7 days accuracies (will average around 93)
    recent_accs = [92.0, 94.0, 93.0, 95.0]
    for i, acc in enumerate(recent_accs):
        items.append(
            EvaluationItem(
                evaluation_id=eval_run.id,
                predicted_receipt_details={"vendor": "Demo Co"},
                predicted_audit_decision={"pass": True},
                correct_receipt_details={"vendor": "Demo Co"},
                correct_audit_decision={"pass": True},
                grader_scores={"accuracy": acc},
                created_at=now - dt.timedelta(days=i),
            )
        )

    # Previous 7 days accuracies (will average around 90)
    prev_accs = [89.0, 90.0, 91.0]
    for i, acc in enumerate(prev_accs, start=8):
        items.append(
            EvaluationItem(
                evaluation_id=eval_run.id,
                predicted_receipt_details={"vendor": "Demo Co"},
                predicted_audit_decision={"pass": True},
                correct_receipt_details={"vendor": "Demo Co"},
                correct_audit_decision={"pass": True},
                grader_scores={"accuracy": acc},
                created_at=now - dt.timedelta(days=i),
            )
        )

    db.add_all(items)
    await db.commit()


async def main():
    await init_db()
    async with AsyncSessionLocal() as db:
        user = await ensure_dev_user(db)
        await seed_receipts(db, user)
        await seed_events(db)
        await seed_support(db, user)
        await seed_evaluations(db, user)
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
