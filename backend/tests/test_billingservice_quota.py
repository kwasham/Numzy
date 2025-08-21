from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.services.billing_service import BillingService
from app.models.enums import PlanType
from app.models.tables import Base, Receipt, User

@pytest.mark.asyncio
async def test_is_over_quota_false_when_under_limit(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        user = User(clerk_id="c1", email="t@example.com", name="T", plan=PlanType.PERSONAL)
        session.add(user); await session.commit(); await session.refresh(user)
        # Add fewer receipts than quota
        for _ in range(3):
            session.add(Receipt(owner_id=user.id, file_path="x", filename="x.jpg", status="PENDING"))
        await session.commit()
        svc = BillingService()
        over = await svc.is_over_quota(session, user)
        assert over is False

@pytest.mark.asyncio
async def test_is_over_quota_true_when_at_or_over_limit():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        user = User(clerk_id="c2", email="t2@example.com", name="T2", plan=PlanType.FREE)
        session.add(user); await session.commit(); await session.refresh(user)
        # FREE quota = 25 (from BillingService matrix). Insert 25 receipts.
        for _ in range(25):
            session.add(Receipt(owner_id=user.id, file_path="x", filename="x.jpg", status="PENDING"))
        await session.commit()
        svc = BillingService()
        over = await svc.is_over_quota(session, user)
        assert over is True
