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
        content=payload,
        headers={"stripe-signature": "stub"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("received") is True
    assert body.get("queued") is True  # async offload path

    # Second call with same id should be deduped
    resp2 = app_client.post(
        "/webhooks/stripe",
        content=payload,
        headers={"stripe-signature": "stub"},
    )
    assert resp2.status_code == 200
    assert resp2.json().get("duplicate") is True


def test_invoice_failed_and_action_required_paths(app_client):
    # payment_failed
    failed_evt = _fake_event("invoice.payment_failed", {"id": "in_test_1", "customer": "cus_123"}, event_id="evt_2")
    resp = app_client.post(
        "/webhooks/stripe",
        content=json.dumps(failed_evt).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    assert resp.status_code == 200

    # action required
    ar_evt = _fake_event("invoice.payment_action_required", {"id": "in_test_2", "customer": "cus_123"}, event_id="evt_3")
    resp2 = app_client.post(
        "/webhooks/stripe",
        content=json.dumps(ar_evt).encode("utf-8"),
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
        content=payload,
        headers={"stripe-signature": "stub"},
    )
    assert resp.status_code in (400, 401)


def test_webhook_allowlist_filters_unlisted_event(monkeypatch, app_client):
    """When STRIPE_WEBHOOK_ALLOWED_EVENTS excludes an event, it should be filtered early."""
    from app.core import config as cfg
    import app.api.routes.stripe_webhooks as wh
    import types

    # Allow only invoice.* events
    monkeypatch.setattr(cfg.settings, "STRIPE_WEBHOOK_ALLOWED_EVENTS", "invoice.*", raising=False)

    # Capture enqueue calls
    calls: list[dict] = []
    monkeypatch.setattr(wh, "process_stripe_event", types.SimpleNamespace(send=lambda evt: calls.append(evt)))

    # Send an event that is NOT allowed (checkout.session.completed)
    filtered_evt = _fake_event("checkout.session.completed", {"id": "cs_f_1"}, event_id="evt_filter_1")
    resp = app_client.post(
        "/webhooks/stripe",
        content=json.dumps(filtered_evt).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("filtered") is True
    assert body.get("queued") is None
    assert calls == []  # ensure we did not enqueue

    # Send an allowed event (invoice.payment_failed) and ensure it queues
    allowed_evt = _fake_event("invoice.payment_failed", {"id": "in_allow_1"}, event_id="evt_allow_1")
    resp2 = app_client.post(
        "/webhooks/stripe",
        content=json.dumps(allowed_evt).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    assert resp2.status_code == 200
    assert resp2.json().get("queued") is True
    assert len(calls) == 1


def test_webhook_allowlist_multiple_patterns(monkeypatch, app_client):
    """Support a comma-separated pattern set; only matching events enqueue."""
    from app.core import config as cfg
    import app.api.routes.stripe_webhooks as wh
    import types

    # Allow only checkout.session.* and invoice.payment_failed
    monkeypatch.setattr(cfg.settings, "STRIPE_WEBHOOK_ALLOWED_EVENTS", "checkout.session.* , invoice.payment_failed", raising=False)

    calls: list[dict] = []
    monkeypatch.setattr(wh, "process_stripe_event", types.SimpleNamespace(send=lambda evt: calls.append(evt)))

    # Allowed (checkout.session.completed)
    evt_allowed = _fake_event("checkout.session.completed", {"id": "cs_multi_1"}, event_id="evt_multi_1")
    r1 = app_client.post(
        "/webhooks/stripe",
        content=json.dumps(evt_allowed).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    assert r1.status_code == 200 and r1.json().get("queued") is True

    # Disallowed (customer.subscription.updated)
    evt_blocked = _fake_event("customer.subscription.updated", {"id": "sub_multi_1"}, event_id="evt_multi_2")
    r2 = app_client.post(
        "/webhooks/stripe",
        content=json.dumps(evt_blocked).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    assert r2.status_code == 200 and r2.json().get("filtered") is True

    # Allowed second pattern (invoice.payment_failed)
    evt_failed = _fake_event("invoice.payment_failed", {"id": "in_multi_1"}, event_id="evt_multi_3")
    r3 = app_client.post(
        "/webhooks/stripe",
        content=json.dumps(evt_failed).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    assert r3.status_code == 200 and r3.json().get("queued") is True
    assert len(calls) == 2  # checkout + failed


def test_invoice_paid_and_payment_succeeded_events(monkeypatch, app_client):
    """Ensure both invoice.paid and invoice.payment_succeeded enqueue when allowed explicitly."""
    from app.core import config as cfg
    import app.api.routes.stripe_webhooks as wh
    import types

    monkeypatch.setattr(cfg.settings, "STRIPE_WEBHOOK_ALLOWED_EVENTS", "invoice.paid,invoice.payment_succeeded", raising=False)
    captured: list[dict] = []
    monkeypatch.setattr(wh, "process_stripe_event", types.SimpleNamespace(send=lambda evt: captured.append(evt)))

    paid_evt = _fake_event("invoice.paid", {"id": "in_paid_1"}, event_id="evt_paid_1")
    succ_evt = _fake_event("invoice.payment_succeeded", {"id": "in_succ_1"}, event_id="evt_succ_1")

    r1 = app_client.post(
        "/webhooks/stripe",
        content=json.dumps(paid_evt).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    r2 = app_client.post(
        "/webhooks/stripe",
        content=json.dumps(succ_evt).encode("utf-8"),
        headers={"stripe-signature": "stub"},
    )
    assert r1.status_code == 200 and r1.json().get("queued") is True
    assert r2.status_code == 200 and r2.json().get("queued") is True
    # Both events captured
    types_set = {e.get("type") for e in captured}
    assert {"invoice.paid", "invoice.payment_succeeded"} <= types_set
