from __future__ import annotations

import types
import pytest

from app.core.tasks import reconcile_pending_subscription_downgrades
from app.models.enums import PlanType
from app.core.config import settings


class DummyUser:
    def __init__(self, plan: PlanType, stripe_customer_id: str, id: int = 1):
        self.plan = plan
        self.stripe_customer_id = stripe_customer_id
        self.id = id


class DummySession:
    def __init__(self, users):
        self._users = users
        self._commits = 0
    def query(self, model):
        class Q:
            def __init__(self, users):
                self._users = users
            def filter(self, *a, **k):
                return self
            def limit(self, n):
                return self
            def all(self):
                return self._users
        return Q(self._users)
    def commit(self):
        self._commits += 1
    def rollback(self):
        pass
    def close(self):
        pass


@pytest.fixture(autouse=True)
def stripe_mock(monkeypatch):
    # Provide stripe module mock
    class Sub:
        def __init__(self):
            self.modified = []
        @staticmethod
        def list(customer=None, status="all", limit=1):  # returns active sub scheduled for downgrade soon
            return {"data": [{
                "id": "sub_123",
                "status": "active",
                "current_period_end": 1000,  # will be within lookahead (we'll monkeypatch time)
                "cancel_at_period_end": True,
                "items": {"data": [{"id": "si_1", "price": {"id": "price_pro_month", "recurring": {"interval": "month"}}}]},
                "metadata": {"pending_plan": "personal"},
            }]}
        @staticmethod
        def modify(sub_id, **kwargs):
            Sub.last_modify = {"sub_id": sub_id, **kwargs}
            return {"id": sub_id, **kwargs}
    Sub.last_modify = {}
    class Stripe:
        Subscription = Sub
    monkeypatch.setattr("app.core.tasks.stripe", Stripe)
    monkeypatch.setattr(settings, "STRIPE_API_KEY", "sk_test_x", raising=False)
    # price env vars
    monkeypatch.setattr(settings, "STRIPE_PRICE_PERSONAL_MONTHLY", "price_personal_month", raising=False)
    monkeypatch.setattr(settings, "STRIPE_PRICE_PRO_MONTHLY", "price_pro_month", raising=False)
    yield


@pytest.fixture(autouse=True)
def session_patch(monkeypatch):
    from app.core import tasks as tasks_mod
    users = [DummyUser(PlanType.PRO, "cus_123")]
    sess = DummySession(users)
    monkeypatch.setattr(tasks_mod, "SessionLocal", lambda: sess)
    # fast time within window
    monkeypatch.setattr(tasks_mod.time, "time", lambda: 995)
    return sess


def test_reconciliation_applies_and_clears_metadata(monkeypatch):
    # Call directly so logic executes synchronously in test process
    reconcile_pending_subscription_downgrades(lookahead_seconds=600, batch_limit=10)
    from app.core.tasks import stripe as stripe_mod  # type: ignore
    args = stripe_mod.Subscription.last_modify
    assert args.get("cancel_at_period_end") is False
    assert "pending_plan" not in (args.get("metadata") or {})
