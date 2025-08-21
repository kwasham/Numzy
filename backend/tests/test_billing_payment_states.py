from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api.routes.billing import router as billing_router
from app.core.database import get_db
from app.api.dependencies import get_user as dep_get_user


class DummyDB:
    async def commit(self):
        return None


async def _yield_db():
    db = DummyDB()
    try:
        yield db
    finally:
        pass


class DummyUser:
    def __init__(self, plan_value="pro", customer_id="cus_pd"):
        from app.models.enums import PlanType
        self.id = 1
        self.email = "pay@example.com"
        self.clerk_id = "clrk_pd"
        try:
            self.plan = PlanType(plan_value)
        except Exception:
            self.plan = PlanType.FREE
        self.stripe_customer_id = customer_id


class StripePastDue:
    class Subscription:
        @staticmethod
        def list(customer=None, status="all", limit=1, expand=None):
            return {
                "data": [{
                    "id": "sub_pd",
                    "status": "past_due",
                    "current_period_end": 1700000000,
                    "items": {"data": [{"price": {"id": "price_pro_month"}}]},
                    "latest_invoice": {
                        "id": "in_pd",
                        "status": "open",
                        "payment_intent": {"id": "pi_pd", "status": "requires_payment_method"},
                    },
                }]
            }


@pytest.fixture(autouse=True)
def base_env(monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_API_KEY", "sk_test_x", raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_month", raising=False)
    yield


def _mk_app(user):
    app = FastAPI()
    app.include_router(billing_router)
    app.dependency_overrides[get_db] = _yield_db
    async def _override_user():
        return user
    app.dependency_overrides[dep_get_user] = _override_user
    return app


def test_status_exposes_past_due(monkeypatch):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripePastDue)

    app = _mk_app(DummyUser())
    client = TestClient(app)

    r = client.get("/billing/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("payment_state") == "past_due"
    # For past_due we don't require action metadata; it may be None
    assert body.get("action") in (None, {})


@pytest.mark.skip(reason="Test Clock integration skeleton; enable in nightly job with real API keys in sandbox.")
def test_testclock_skeleton_documentation_only():
    """
    Skeleton (intentionally skipped):
    - Create a Test Clock
    - Create Customer attached to clock and a subscription
    - Advance clock, assert webhook processing and /billing/status transitions
    This follows Stripe docs: billing/testing/test-clocks.
    """
    pass
