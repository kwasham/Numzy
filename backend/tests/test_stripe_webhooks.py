from __future__ import annotations

import json
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the real router to test wiring and handler behavior
from app.api.routes.stripe_webhooks import router as stripe_router


@pytest.fixture(scope="module")
def app_client():
    app = FastAPI()
    app.include_router(stripe_router)
    client = TestClient(app)
    return client


def _fake_event(event_type: str, data_object: dict, event_id: str = "evt_test_1"):
    return {
        "id": event_id,
        "type": event_type,
        "data": {"object": data_object},
    }


class DummyStripe:
    class error:
        class SignatureVerificationError(Exception):
            pass

    class Webhook:
        calls = []

        @staticmethod
        def construct_event(payload, sig_header, secret):
            DummyStripe.Webhook.calls.append((payload, sig_header, secret))
            # Accept any payload when secret matches "good"
            if secret != "good":
                raise DummyStripe.error.SignatureVerificationError("bad secret")
            return json.loads(payload.decode("utf-8"))


@pytest.fixture(autouse=True)
def patch_stripe(monkeypatch):
    # Patch stripe module used in router
    import app.api.routes.stripe_webhooks as wh
    monkeypatch.setattr(wh, "stripe", DummyStripe)
    # Patch settings to provide webhook secrets and redis url
    from app.core import config as cfg
    monkeypatch.setattr(cfg.settings, "STRIPE_WEBHOOK_SECRET", None, raising=False)
    monkeypatch.setattr(cfg.settings, "STRIPE_WEBHOOK_SECRETS", "bad, good", raising=False)
    monkeypatch.setattr(cfg.settings, "REDIS_URL", "redis://localhost:6379/15", raising=False)
    # Patch redis client used for dedup to a dummy
    class DummyRedis:
        def __init__(self):
            self.store = set()
        @classmethod
        def from_url(cls, url, decode_responses=True):
            return cls()
        def set(self, name, value, nx=True, ex=None):
            if name in self.store:
                return False
            self.store.add(name)
            return True
    _redis_singleton = DummyRedis()
    monkeypatch.setattr(wh, "_get_redis_client", lambda: _redis_singleton)
    # Patch Dramatiq send to no-op
    monkeypatch.setattr(wh, "process_stripe_event", types.SimpleNamespace(send=lambda evt: None))
    yield


def test_webhook_multi_secret_and_dedup(app_client):
    event = _fake_event("checkout.session.completed", {"id": "cs_test_1"})
    payload = json.dumps(event).encode("utf-8")

    # First call should be processed (not duplicate)
    resp = app_client.post(
        "/webhooks/stripe",
        data=payload,
        headers={"stripe-signature": "stub"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("received") is True
    assert body.get("queued") is True  # async offload path

    # Second call with same id should be deduped
    resp2 = app_client.post(
        "/webhooks/stripe",
        data=payload,
        headers={"stripe-signature": "stub"},
    )
    assert resp2.status_code == 200
    assert resp2.json().get("duplicate") is True


def test_invoice_failed_and_action_required_paths(app_client):
    # payment_failed
    failed_evt = _fake_event("invoice.payment_failed", {"id": "in_test_1", "customer": "cus_123"}, event_id="evt_2")
    resp = app_client.post(
        "/webhooks/stripe",
        data=json.dumps(failed_evt).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    assert resp.status_code == 200

    # action required
    ar_evt = _fake_event("invoice.payment_action_required", {"id": "in_test_2", "customer": "cus_123"}, event_id="evt_3")
    resp2 = app_client.post(
        "/webhooks/stripe",
        data=json.dumps(ar_evt).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    assert resp2.status_code == 200


def test_webhook_rejects_when_all_secrets_invalid(monkeypatch, app_client):
    """If none of the configured secrets validate, the endpoint should 400."""
    from app.core import config as cfg
    # Force only bad secrets so DummyStripe.Webhook raises every time
    monkeypatch.setattr(cfg.settings, "STRIPE_WEBHOOK_SECRETS", "bad", raising=False)

    event = _fake_event("checkout.session.completed", {"id": "cs_bad"}, event_id="evt_bad")
    payload = json.dumps(event).encode("utf-8")

    resp = app_client.post(
        "/webhooks/stripe",
        data=payload,
        headers={"stripe-signature": "stub"},
    )
    assert resp.status_code in (400, 401)
