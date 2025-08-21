from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.billing import router as billing_router
from app.api.routes.stripe_webhooks import router as webhook_router
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
    def __init__(self, plan_value="pro", customer_id="cus_fail"):
        from app.models.enums import PlanType
        self.id = 2
        self.email = "fail@example.com"
        self.clerk_id = "clrk_fail"
        try:
            self.plan = PlanType(plan_value)
        except Exception:
            self.plan = PlanType.FREE
        self.stripe_customer_id = customer_id

@pytest.fixture(autouse=True)
def base_env(monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_API_KEY", "sk_test_x", raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_month", raising=False)
    yield

def _mk_app(user):
    app = FastAPI()
    app.include_router(billing_router)
    app.include_router(webhook_router)
    app.dependency_overrides[get_db] = _yield_db
    async def _override_user():
        return user
    app.dependency_overrides[dep_get_user] = _override_user
    return app

class StripeNoop:
    class Subscription:
        @staticmethod
        def list(customer=None, status="all", limit=1, expand=None):
            return {"data": []}

@pytest.mark.parametrize("event_type", ["invoice.payment_failed", "invoice.payment_action_required"])
def test_webhook_invoice_states(monkeypatch, event_type):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, "stripe", StripeNoop)

    app = _mk_app(DummyUser())
    client = TestClient(app)

    payload = {
        "id": "evt_123",
        "type": event_type,
        "data": {
            "object": {
                "id": "in_test",
                "customer": "cus_fail",
                "subscription": "sub_123",
                "attempt_count": 1,
                "lines": {"data": [{"price": {"id": "price_pro_month"}}]},
            }
        }
    }
    # Directly call handler (signature bypass) by posting JSON; signature path tested elsewhere
    r = client.post("/stripe/webhook", json=payload)
    assert r.status_code == 200
    # Check status endpoint reflects known plan still (no downgrade) and exposes payment_state or action meta indirectly
    status = client.get("/billing/status").json()
    assert status.get("plan") in ("pro", "PRO")
    # We don't force payment_state on action_required until subscription fetch; just ensure endpoint returns JSON
    assert "catalog" in status
