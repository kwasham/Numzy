import pytest

from app.models.enums import PlanType
from app.models.tables import User
from app.services.billing_service import BillingService


def _make_user(plan: PlanType):
    return User(email="quota_logic@example.com", name="Quota Logic", clerk_id="clk_quota", plan=plan)


@pytest.mark.asyncio
async def test_quota_enforcement_counter_only():
    """Lightweight integration: verify BillingService transitions from under quota to over quota using the counter."""
    user = _make_user(PlanType.PERSONAL)
    user.monthly_receipt_count = 99
    svc = BillingService()
    assert await svc.is_over_quota(None, user) is False  # type: ignore[arg-type]
    user.monthly_receipt_count = 100
    assert await svc.is_over_quota(None, user) is True  # type: ignore[arg-type]
