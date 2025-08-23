from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.billing import router as billing_router
from app.core.database import get_db
from app.api.dependencies import get_user as dep_get_user
from app.models.enums import PlanType


class DummyDB:
    async def commit(self):
        return True


async def _yield_db():
    db = DummyDB()
    try:
        yield db
    finally:
        pass


class DummyUser:
    def __init__(self, plan_value="pro", customer_id="cus_intv"):
        self.id = 1
        self.email = "interval@example.com"
        self.clerk_id = "clrk_intv"
        self.plan = PlanType.PRO if plan_value == "pro" else PlanType.PERSONAL
        self.stripe_customer_id = customer_id


def _mk_app(user: DummyUser):
    app = FastAPI()
    app.include_router(billing_router)
    app.dependency_overrides[get_db] = _yield_db
    async def _override_user():
        return user
    app.dependency_overrides[dep_get_user] = _override_user
    return app


class StripeIntervalSwitch:
    class Price:
        @staticmethod
        def retrieve(price_id):
            # Provide monthly vs yearly price objects with recurring metadata
            mapping = {
                "price_pro_month": {"unit_amount": 2000, "recurring": {"interval": "month", "interval_count": 1}},
                # yearly price provides discount: 20 * 12 * 0.83 ≈ 19920 cents
                "price_pro_year": {"unit_amount": 19920, "recurring": {"interval": "year", "interval_count": 1}},
            }
            base = mapping.get(price_id, {"unit_amount": 0})
            return {"id": price_id, **base, "currency": "usd"}
    class Subscription:
        @staticmethod
        def list(customer=None, status="all", limit=2):
            return {"data": [{
                "id": "sub_intv",
                "status": "active",
                "current_period_end": 1700000000,
                "items": {"data": [{"id": "si_intv", "price": {"id": "price_pro_month"}}]},
                "metadata": {},
            }]}
        @staticmethod
        def modify(sub_id, **kwargs):
            StripeIntervalSwitch.last_modify_args = {"sub_id": sub_id, **kwargs}
            return {"id": sub_id, **kwargs}

StripeIntervalSwitch.last_modify_args = {}


def test_interval_switch_monthly_to_yearly_normalized(monkeypatch):
    # Configure environment with both monthly and yearly price IDs
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_API_KEY", "sk_test_x", raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_month", raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_YEARLY", "price_pro_year", raising=False)

    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeIntervalSwitch)

    user = DummyUser(plan_value="pro")
    app = _mk_app(user)
    client = TestClient(app)

    # Switching same plan but monthly -> yearly should be considered an upgrade if yearly normalized monthly is higher
    # Here yearly normalized = 19920 / 12 = 1660 vs monthly 2000, so it's actually a downgrade in normalized monthly spend
    # We expect no upgrade classification (is_upgrade False) and no deferred downgrade logic because same plan different interval.
    r = client.post("/billing/subscription/change", json={"target_plan": "pro", "interval": "yearly"})
    assert r.status_code == 200
    body = r.json()
    # unchanged flag should not trigger because price id differs
    assert body["upgrade"] is False
    # Ensure Stripe modify was called with yearly price id
    args = StripeIntervalSwitch.last_modify_args
    items = args.get("items")
    assert isinstance(items, list) and items[0]["price"] == "price_pro_year"
    # No cancel_at_period_end for interval switch
    assert args.get("cancel_at_period_end") is False
