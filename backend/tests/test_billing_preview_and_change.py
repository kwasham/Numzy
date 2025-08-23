from __future__ import annotations

import pytest
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
    def __init__(self, plan_value="pro", customer_id="cus_prev"):
        self.id = 1
        self.email = "preview@example.com"
        self.clerk_id = "clrk_prev"
        try:
            self.plan = PlanType(plan_value)
        except Exception:
            self.plan = PlanType.FREE
        self.stripe_customer_id = customer_id


def _mk_app(user: DummyUser):
    app = FastAPI()
    app.include_router(billing_router)
    app.dependency_overrides[get_db] = _yield_db
    async def _override_user():
        return user
    app.dependency_overrides[dep_get_user] = _override_user
    return app


class StripePreview:
    class Price:
        @staticmethod
        def retrieve(price_id):
            # Return distinct unit_amount for plan price IDs
            mapping = {
                "price_pro_month": 2000,
                "price_personal_month": 900,
                "price_business_month": 5000,
            }
            return {"id": price_id, "unit_amount": mapping.get(price_id, 0), "currency": "usd"}
    class Subscription:
        @staticmethod
        def list(customer=None, status="all", limit=1):
            # Current subscription is pro monthly by default
            return {"data": [{
                "id": "sub_prev",
                "status": "active",
                "items": {"data": [{"price": {"id": "price_pro_month"}}]},
            }]}


class StripeChange(StripePreview):
    class Subscription:
        @staticmethod
        def list(customer=None, status="all", limit=2):
            return {"data": [{
                "id": "sub_change",
                "status": "active",
                "current_period_end": 1700000000,
                "items": {"data": [{"id": "si_1", "price": {"id": "price_pro_month"}}]},
                "metadata": {},
            }]}
        @staticmethod
        def modify(sub_id, **kwargs):
            # Echo back kwargs for inspection
            # capture for test assertions
            StripeChange.last_modify_args = {"sub_id": sub_id, **kwargs}
            d = {"id": sub_id, **kwargs}
            return d

StripeChange.last_modify_args = {}


class StripeChangeUpgrade(StripePreview):
    class Subscription:
        @staticmethod
        def list(customer=None, status="all", limit=2):
            # Current plan personal -> upgrading to pro
            return {"data": [{
                "id": "sub_change_up",
                "status": "active",
                "current_period_end": 1700000000,
                "items": {"data": [{"id": "si_up", "price": {"id": "price_personal_month"}}]},
                "metadata": {},
            }]}
        @staticmethod
        def modify(sub_id, **kwargs):
            StripeChangeUpgrade.last_modify_args = {"sub_id": sub_id, **kwargs}
            return {"id": sub_id, **kwargs}

StripeChangeUpgrade.last_modify_args = {}


@pytest.fixture(autouse=True)
def base_env(monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_API_KEY", "sk_test_x", raising=False)
    # Map env price IDs
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_month", raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PERSONAL_MONTHLY", "price_personal_month", raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_BUSINESS_MONTHLY", "price_business_month", raising=False)
    # Ensure yearly unset to test monthly fallback
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_YEARLY", None, raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PERSONAL_YEARLY", None, raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_BUSINESS_YEARLY", None, raising=False)
    yield


def test_preview_upgrade(monkeypatch):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripePreview)
    user = DummyUser(plan_value="personal")
    app = _mk_app(user)
    client = TestClient(app)
    # Preview moving to business (higher amount vs current pro? we set current to pro -> so business is upgrade)
    r = client.post("/billing/subscription/preview", json={"target_plan": "business", "interval": "monthly"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_amount"] == 20.00  # pro
    assert data["new_amount"] == 50.00
    assert data["is_upgrade"] is True


def test_preview_downgrade(monkeypatch):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripePreview)
    user = DummyUser(plan_value="pro")
    app = _mk_app(user)
    client = TestClient(app)
    r = client.post("/billing/subscription/preview", json={"target_plan": "personal"})
    assert r.status_code == 200
    data = r.json()
    assert data["current_amount"] == 20.00
    assert data["new_amount"] == 9.00
    assert data["is_upgrade"] is False


def test_preview_no_op_same_plan(monkeypatch):
    class StripePreviewSame(StripePreview):
        class Subscription:
            @staticmethod
            def list(customer=None, status="all", limit=1):
                return {"data": [{
                    "id": "sub_prev_same",
                    "status": "active",
                    "items": {"data": [{"price": {"id": "price_pro_month"}}]},
                }]}
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripePreviewSame)
    user = DummyUser(plan_value="pro")
    app = _mk_app(user)
    client = TestClient(app)
    r = client.post("/billing/subscription/preview", json={"target_plan": "pro"})
    assert r.status_code == 200
    body = r.json()
    assert body["difference"] == 0
    assert body["is_upgrade"] is False


def test_change_deferred_downgrade_sets_pending_plan(monkeypatch):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeChange)
    user = DummyUser(plan_value="pro")
    app = _mk_app(user)
    client = TestClient(app)
    r = client.post("/billing/subscription/change", json={"target_plan": "personal", "defer_downgrade": True})
    assert r.status_code == 200
    body = r.json()
    # Expect deferred flag true and not immediate upgrade
    assert body["deferred"] is True
    assert body["upgrade"] is False
    # Verify Stripe modify called with cancel_at_period_end True and metadata marker
    args = StripeChange.last_modify_args
    assert args.get("cancel_at_period_end") is True
    # downgrade scheduling should not include immediate proration invoice
    assert args.get("proration_behavior") in (None, "none")
    meta = args.get("metadata") or {}
    assert meta.get("pending_plan") == "personal"


def test_change_upgrade_immediate_proration(monkeypatch):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeChangeUpgrade)
    user = DummyUser(plan_value="personal")
    app = _mk_app(user)
    client = TestClient(app)
    r = client.post("/billing/subscription/change", json={"target_plan": "pro"})
    assert r.status_code == 200
    body = r.json()
    assert body["upgrade"] is True
    assert body["deferred"] is False
    args = StripeChangeUpgrade.last_modify_args
    assert args.get("cancel_at_period_end") is False
    # items list should contain new pro price id
    items = args.get("items")
    assert isinstance(items, list) and items[0].get("price") == "price_pro_month"
    # upgrade must request proration invoice creation
    assert args.get("proration_behavior") == "create_invoice"
