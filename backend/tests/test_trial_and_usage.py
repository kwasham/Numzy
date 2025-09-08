import datetime as dt
import pytest

from app.models.tables import User
from app.models.enums import PlanType
from app.services.trial_service import TrialService, DEFAULT_TRIAL_DAYS
from app.services.billing_service import BillingService


def _make_user(plan: PlanType):
    # Minimal user object (no DB persistence needed for pure logic tests)
    return User(email="logic@example.com", name="Logic User", clerk_id="clrk_logic", plan=plan)


def test_trial_starts_on_first_upload():
    user = _make_user(PlanType.FREE)
    assert user.trial_started_at is None
    ts = TrialService()
    started = ts.ensure_trial(user, now=dt.datetime.utcnow())
    assert started is True
    assert user.trial_started_at is not None
    assert user.trial_ends_at is not None
    assert (user.trial_ends_at - user.trial_started_at).days == DEFAULT_TRIAL_DAYS


def test_monthly_counter_reset():
    user = _make_user(PlanType.FREE)
    ts = TrialService()
    now = dt.datetime(2025, 9, 2, 12, 0, 0)
    ts.ensure_trial(user, now=now)
    user.monthly_receipt_count = 5
    user.last_receipt_reset_at = dt.datetime(2025, 8, 31, 23, 0, 0)
    reset = ts.maybe_reset_monthly_counter(user, now=now)
    assert reset is True
    assert user.monthly_receipt_count == 0


@pytest.mark.asyncio
async def test_billing_service_counter_usage():
    user = _make_user(PlanType.PERSONAL)
    user.monthly_receipt_count = 99
    svc = BillingService()
    # Provide dummy db session None since fallback query not needed
    assert await svc.is_over_quota(None, user) is False  # type: ignore[arg-type]
    user.monthly_receipt_count = 100
    assert await svc.is_over_quota(None, user) is True  # type: ignore[arg-type]

