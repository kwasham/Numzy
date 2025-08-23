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
    def __init__(self):
        from app.models.enums import PlanType
        self.id = 99
        self.email = 'persist@example.com'
        self.clerk_id = 'clrk_persist'
        self.plan = PlanType.PRO
        self.stripe_customer_id = 'cus_persist'
        # Pretend webhook already persisted these fields
        self.subscription_status = 'active'
        self.payment_state = 'requires_action'
        self.last_invoice_status = 'action_required'

class StripeNoop:
    class Subscription:
        @staticmethod
        def list(customer=None, status='all', limit=1, expand=None):
            # Return empty so endpoint falls back to persisted fields
            return {'data': []}

@pytest.fixture(autouse=True)
def base_env(monkeypatch):
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, 'STRIPE_API_KEY', 'sk_test_x', raising=False)
    yield

def _mk_app(user):
    app = FastAPI()
    app.include_router(billing_router)
    app.dependency_overrides[get_db] = _yield_db
    async def _override_user():
        return user
    app.dependency_overrides[dep_get_user] = _override_user
    return app


def test_status_uses_persisted_fields(monkeypatch):
    import app.api.routes.billing as billing_mod
    monkeypatch.setattr(billing_mod, 'stripe', StripeNoop)

    app = _mk_app(DummyUser())
    client = TestClient(app)
    r = client.get('/billing/status')
    assert r.status_code == 200
    body = r.json()
    assert body['payment_state'] == 'requires_action'
    assert body['subscription_status'] == 'active'
    assert body['last_invoice_status'] == 'action_required'
