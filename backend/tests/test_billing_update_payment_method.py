from __future__ import annotations

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


class DummyUser:
    def __init__(self, email="pmtest@example.com", clerk_id="clrk_pm", customer_id="cus_abc"):
        self.id = 1
        self.email = email
        self.clerk_id = clerk_id
        self.stripe_customer_id = customer_id


def _mk_app(override_user: DummyUser, override_db_cm):
    app = FastAPI()
    app.include_router(billing_router)
    app.dependency_overrides[get_db] = override_db_cm
    async def _override_user():
        return override_user
    app.dependency_overrides[dep_get_user] = _override_user
    return app


class StripeForUpdatePM:
    class state:
        attach_calls = []
        modify_calls = []
        paid_invoice_ids = []
        pm_attached = False
        customer_id = "cus_abc"

    class Subscription:
        @staticmethod
        def retrieve(subscription_id):
            return {"id": subscription_id, "customer": StripeForUpdatePM.state.customer_id}

        @staticmethod
        def modify(subscription_id, default_payment_method=None):
            StripeForUpdatePM.state.modify_calls.append({
                "subscription_id": subscription_id,
                "default_payment_method": default_payment_method,
            })
            return {"id": subscription_id, "default_payment_method": default_payment_method}

    class PaymentMethod:
        @staticmethod
        def retrieve(payment_method_id):
            if StripeForUpdatePM.state.pm_attached:
                return {"id": payment_method_id, "customer": StripeForUpdatePM.state.customer_id}
            return {"id": payment_method_id}

        @staticmethod
        def attach(payment_method_id, customer=None):
            StripeForUpdatePM.state.attach_calls.append({
                "payment_method_id": payment_method_id,
                "customer": customer,
            })
            StripeForUpdatePM.state.pm_attached = True
            return {"id": payment_method_id, "customer": customer}

    class Invoice:
        @staticmethod
        def pay(invoice_id):
            StripeForUpdatePM.state.paid_invoice_ids.append(invoice_id)
            return {"id": invoice_id, "paid": True}


@pytest.fixture(autouse=True)
def set_base_env(monkeypatch):
    # Ensure API key present
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_API_KEY", "sk_test_x", raising=False)
    monkeypatch.setattr(cfg.settings, "FRONTEND_BASE_URL", "http://localhost:3000", raising=False)
    # Reset stub state
    StripeForUpdatePM.state.attach_calls = []
    StripeForUpdatePM.state.modify_calls = []
    StripeForUpdatePM.state.paid_invoice_ids = []
    StripeForUpdatePM.state.pm_attached = False
    StripeForUpdatePM.state.customer_id = "cus_abc"
    yield


def test_update_pm_attaches_and_pays_invoice(monkeypatch):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeForUpdatePM)

    app = _mk_app(DummyUser(), _yield_db)
    client = TestClient(app)

    # Start with PM not attached; endpoint should attach and set default, then pay invoice
    body = {"subscription_id": "sub_123", "payment_method_id": "pm_123", "invoice_id": "in_99"}
    r = client.post("/billing/subscription/payment-method", json=body)
    # debug output
    print("RESP1:", r.status_code, r.text)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["subscription_id"] == "sub_123"
    assert data["payment_method_id"] == "pm_123"
    assert data["invoice_paid"] is True

    # Validate Stripe calls
    assert len(StripeForUpdatePM.state.attach_calls) == 1
    assert StripeForUpdatePM.state.attach_calls[0]["customer"] == "cus_abc"
    assert len(StripeForUpdatePM.state.modify_calls) == 1
    assert StripeForUpdatePM.state.modify_calls[0]["default_payment_method"] == "pm_123"
    assert StripeForUpdatePM.state.paid_invoice_ids == ["in_99"]


def test_update_pm_already_attached_no_invoice(monkeypatch):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeForUpdatePM)

    # Simulate PM already attached
    StripeForUpdatePM.state.pm_attached = True

    app = _mk_app(DummyUser(), _yield_db)
    client = TestClient(app)

    body = {"subscription_id": "sub_456", "payment_method_id": "pm_attached"}
    r = client.post("/billing/subscription/payment-method", json=body)
    print("RESP2:", r.status_code, r.text)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["invoice_paid"] is False

    # No attach called; modify called once
    assert len(StripeForUpdatePM.state.attach_calls) == 0
    assert len(StripeForUpdatePM.state.modify_calls) == 1
    assert StripeForUpdatePM.state.modify_calls[0]["subscription_id"] == "sub_456"
    assert StripeForUpdatePM.state.modify_calls[0]["default_payment_method"] == "pm_attached"


def test_update_pm_subscription_without_customer_returns_404(monkeypatch):
    import app.api.routes.billing as billing_mod

    class StripeNoCustomer(StripeForUpdatePM):
        class Subscription(StripeForUpdatePM.Subscription):
            @staticmethod
            def retrieve(subscription_id):
                return {"id": subscription_id}  # no customer key

    monkeypatch.setattr(billing_mod, "stripe", StripeNoCustomer)

    app = _mk_app(DummyUser(), _yield_db)
    client = TestClient(app)

    body = {"subscription_id": "sub_no_cus", "payment_method_id": "pm_1"}
    r = client.post("/billing/subscription/payment-method", json=body)
    assert r.status_code == 404
