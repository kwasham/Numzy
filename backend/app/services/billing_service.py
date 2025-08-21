"""Billing service providing plan limits & usage enforcement.

This module centralises pricing/plan enforcement logic so API route
handlers remain thin. It purposefully does NOT talk to Stripe for
metered billing (out of scope) but exposes clear extension points for
future overage charging.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional, Dict, Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PlanType
from app.models.tables import Receipt, User


@dataclass(frozen=True)
class PlanLimits:
    plan: PlanType
    monthly_quota: float  # receipts per calendar month (inf => unlimited)
    retention_days: Optional[int]  # None => unlimited / custom policy
    priority_support: bool
    advanced_analytics: bool
    sso: bool
    custom_retention: bool


PLAN_LIMIT_MATRIX: Dict[PlanType, PlanLimits] = {
    PlanType.FREE: PlanLimits(
        plan=PlanType.FREE,
        monthly_quota=25,
        retention_days=30,
        priority_support=False,
        advanced_analytics=False,
        sso=False,
        custom_retention=False,
    ),
    PlanType.PERSONAL: PlanLimits(
        plan=PlanType.PERSONAL,
        monthly_quota=100,
        retention_days=180,
        priority_support=False,
        advanced_analytics=False,
        sso=False,
        custom_retention=False,
    ),
    PlanType.PRO: PlanLimits(
        plan=PlanType.PRO,
        monthly_quota=500,
        retention_days=365,
        priority_support=True,
        advanced_analytics=True,
        sso=False,
        custom_retention=False,
    ),
    PlanType.BUSINESS: PlanLimits(
        plan=PlanType.BUSINESS,
        monthly_quota=5000,
        retention_days=None,  # custom
        priority_support=True,
        advanced_analytics=True,
        sso=True,
        custom_retention=True,
    ),
    PlanType.ENTERPRISE: PlanLimits(
        plan=PlanType.ENTERPRISE,
        monthly_quota=float("inf"),
        retention_days=None,
        priority_support=True,
        advanced_analytics=True,
        sso=True,
        custom_retention=True,
    ),
}


class BillingService:
    """Encapsulates plan limit queries & quota enforcement."""

    def get_limits(self, plan: PlanType | None) -> PlanLimits:
        return PLAN_LIMIT_MATRIX.get(plan or PlanType.FREE, PLAN_LIMIT_MATRIX[PlanType.FREE])

    # --- Quota helpers -------------------------------------------------
    def get_monthly_quota(self, plan: PlanType | None) -> float:
        return self.get_limits(plan).monthly_quota

    async def get_monthly_usage(self, db: AsyncSession, user_id: int, when: Optional[dt.datetime] = None) -> int:
        when = when or dt.datetime.utcnow()
        start = dt.datetime(when.year, when.month, 1, tzinfo=dt.timezone.utc)
        if when.month == 12:
            end = dt.datetime(when.year + 1, 1, 1, tzinfo=dt.timezone.utc)
        else:
            end = dt.datetime(when.year, when.month + 1, 1, tzinfo=dt.timezone.utc)
        q = select(func.count(Receipt.id)).where(
            Receipt.owner_id == user_id,
            Receipt.created_at >= start,
            Receipt.created_at < end,
        )
        result = await db.execute(q)
        return int(result.scalar() or 0)

    async def is_over_quota(self, db: AsyncSession, user: User) -> bool:
        quota = self.get_monthly_quota(user.plan)
        if quota == float("inf"):
            return False
        usage = await self.get_monthly_usage(db, user.id)
        return usage >= quota

    async def enforce_quota(self, db: AsyncSession, user: User):
        if await self.is_over_quota(db, user):
            from fastapi import HTTPException
            raise HTTPException(status_code=402, detail="Monthly quota exceeded for plan")

    # --- Retention helpers ---------------------------------------------
    def get_retention_days(self, plan: PlanType | None) -> Optional[int]:
        return self.get_limits(plan).retention_days

    def has_custom_retention(self, plan: PlanType | None) -> bool:
        return self.get_limits(plan).custom_retention

    # --- Feature flags -------------------------------------------------
    def feature_flags(self, plan: PlanType | None) -> Dict[str, bool]:
        limits = self.get_limits(plan)
        return {
            "priority_support": limits.priority_support,
            "advanced_analytics": limits.advanced_analytics,
            "sso": limits.sso,
            "custom_retention": limits.custom_retention,
        }

    # --- Placeholder future extension ---------------------------------
    def record_usage(self, user_id: int, count: int) -> None:  # pragma: no cover - extension point
        """Placeholder for a future aggregation or Stripe metered usage call."""
        return

__all__ = [
    "BillingService",
    "PlanLimits",
    "PLAN_LIMIT_MATRIX",
]