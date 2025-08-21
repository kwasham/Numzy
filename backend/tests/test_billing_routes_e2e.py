from __future__ import annotations

import json
import types
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.billing import router as billing_router
from app.core.database import get_db
from app.api.dependencies import get_user as dep_get_user


class DummyDB:
    def __init__(self):
        self.commits = 0
    async def commit(self):
        self.commits += 1


async def _yield_db():
    db = DummyDB()
    try:
        yield db
    finally:
        pass


from app.models.enums import PlanType


class DummyUser:
    def __init__(self, email="e2e@example.com", clerk_id="clrk_1", plan_value="free", customer_id="cus_123"):
        # SQLA model-like attributes
        self.id = 1
        self.email = email
        self.clerk_id = clerk_id
        # Use PlanType to match route normalization path
        try:
            self.plan = PlanType(plan_value)
        except Exception:
            self.plan = PlanType.FREE
        self.stripe_customer_id = customer_id


class StripeForReconViaID:
    class Price:
        @staticmethod
        def retrieve(price_id):
            # Catalog retrieval
            return {"id": price_id, "unit_amount": 1200, "currency": "usd"}
    class Subscription:
        @staticmethod
        def list(customer=None, status="all", limit=1, **kwargs):
            return {
                "data": [{
                    "id": "sub_1",
                    "status": "active",
                    "current_period_end": 1700000000,
                    "items": {"data": [{"price": {"id": "price_pro_month"}}]},
                }]
            }


class StripeForReconViaLookupKey:
    class Price:
        @staticmethod
        def retrieve(price_id):
            # Return lookup_key for mapping
            return {"id": price_id, "lookup_key": "plan:pro:monthly", "unit_amount": 1200, "currency": "usd"}
        @staticmethod
        def list(lookup_keys=None, active=True, limit=1):
            return {"data": []}
    class Subscription:
        @staticmethod
        def list(customer=None, status="all", limit=1, **kwargs):
            return {
                "data": [{
                    "id": "sub_2",
                    "status": "active",
                    "current_period_end": 1700000000,
                    "items": {"data": [{"price": {"id": "price_unknown_maps_via_lookup"}}]},
                }]
            }


class StripeForPortal:
    class billing_portal:
        class Session:
            captured = None
            @staticmethod
            def create(**kwargs):
                StripeForPortal.billing_portal.Session.captured = kwargs
                return {"url": "https://portal.example/sess"}
    class Customer:
        @staticmethod
        def list(email=None, limit=1):
            return {"data": [{"id": "cus_123"}]}


class StripeForPaymentStates:
    class Subscription:
        @staticmethod
        def list(customer=None, status="all", limit=1, expand=None):
            # Simulate requires_action on payment_intent via expanded invoice
            return {
                "data": [{
                    "id": "sub_pa",
                    "status": "active",
                    "current_period_end": 1700000000,
                    "items": {"data": [{"price": {"id": "price_pro_month"}}]},
                    "latest_invoice": {
                        "id": "in_1",
                        "payment_intent": {"id": "pi_1", "status": "requires_action", "client_secret": "sec_123"},
                    },
                }]
            }
        @staticmethod
        def retrieve(subscription_id, expand=None):
            return {
                "id": subscription_id,
                "latest_invoice": {
                    "id": "in_1",
                    "payment_intent": {"id": "pi_1", "client_secret": "sec_123"},
                },
            }
    class Invoice:
        @staticmethod
        def retrieve(invoice_id, expand=None):
            return {
                "id": invoice_id,
                "payment_intent": {"id": "pi_2", "client_secret": "sec_456"},
            }


@pytest.fixture(autouse=True)
def set_base_env(monkeypatch):
    # Ensure API key present
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_API_KEY", "sk_test_x", raising=False)
    monkeypatch.setattr(cfg.settings, "FRONTEND_BASE_URL", "http://localhost:3000", raising=False)
    yield


def _mk_app(override_user: DummyUser, override_db_cm):
    app = FastAPI()
    app.include_router(billing_router)
    app.dependency_overrides[get_db] = override_db_cm
    async def _override_user():
        return override_user
    app.dependency_overrides[dep_get_user] = _override_user
    return app


def test_status_reconciles_plan_by_env_price_id(monkeypatch):
    # settings map env price ID
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_month", raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_YEARLY", None, raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_TEAM_MONTHLY", None, raising=False)

    # Patch Stripe
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeForReconViaID)

    user = DummyUser(plan_value="free", customer_id="cus_123")
    app = _mk_app(user, _yield_db)
    client = TestClient(app)

    r = client.get("/billing/status")
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] in ("pro", "PRO", "Pro")  # normalized to value by route


def test_status_reconciles_plan_via_lookup_key(monkeypatch):
    # Emulate lookup key mapping without env id match
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_MONTHLY", None, raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_YEARLY", None, raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_TEAM_MONTHLY", None, raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_LOOKUP_PRO_MONTHLY", "plan:pro:monthly", raising=False)

    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeForReconViaLookupKey)

    user = DummyUser(plan_value="free", customer_id="cus_999")
    app = _mk_app(user, _yield_db)
    client = TestClient(app)

    r = client.get("/billing/status")
    assert r.status_code == 200
    assert r.json()["plan"] in ("pro", "PRO", "Pro")


def test_portal_uses_configuration_id(monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_PORTAL_CONFIGURATION_ID", "pcfg_123", raising=False)

    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeForPortal)

    user = DummyUser(plan_value="free", customer_id=None)  # will be created via Customer.list
    app = _mk_app(user, _yield_db)
    client = TestClient(app)

    r = client.post("/billing/portal")
    assert r.status_code == 200
    # Check that configuration was passed through
    captured = StripeForPortal.billing_portal.Session.captured
    assert captured is not None
    assert captured.get("configuration") == "pcfg_123"


def test_status_exposes_requires_action_and_action_meta(monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_month", raising=False)

    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeForPaymentStates)

    user = DummyUser(plan_value="pro", customer_id="cus_act")
    app = _mk_app(user, _yield_db)
    client = TestClient(app)

    r = client.get("/billing/status")
    assert r.status_code == 200
    body = r.json()
    assert body["payment_state"] == "requires_action"
    assert body["action"]["invoice_id"] == "in_1"
    assert body["action"]["payment_intent_id"] == "pi_1"


def test_get_payment_intent_client_secret_by_subscription_or_invoice(monkeypatch):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeForPaymentStates)

    app = _mk_app(DummyUser(), _yield_db)
    client = TestClient(app)

    r = client.get("/billing/payment-intent", params={"subscription_id": "sub_pa"})
    assert r.status_code == 200
    assert r.json()["client_secret"] == "sec_123"

    r2 = client.get("/billing/payment-intent", params={"invoice_id": "in_2"})
    assert r2.status_code == 200
    assert r2.json()["client_secret"] == "sec_456"
