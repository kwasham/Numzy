from __future__ import annotations

import json
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.stripe_webhooks import router as stripe_router


def test_async_offload_path_returns_200_quickly(monkeypatch):
    # Patch stripe verification to accept any payload
    import app.api.routes.stripe_webhooks as wh

    class OKStripe:
        class error:
            class SignatureVerificationError(Exception):
                pass
        class Webhook:
            @staticmethod
            def construct_event(payload, sig_header, secret):
                return json.loads(payload.decode("utf-8"))

    monkeypatch.setattr(wh, "stripe", OKStripe)

    # Use single secret from settings
    from app.core import config as cfg
    monkeypatch.setattr(cfg, "get_webhook_secret_list", lambda: ["good"])  # bypass settings

    # Dedup dummy
    monkeypatch.setattr(wh, "_get_redis_client", lambda: types.SimpleNamespace(set=lambda **kw: True))

    # Patch process_stripe_event to detect it was called
    called = {"sent": False}
    monkeypatch.setattr(wh, "process_stripe_event", types.SimpleNamespace(send=lambda evt: called.__setitem__("sent", True)))

    app = FastAPI()
    app.include_router(stripe_router)
    client = TestClient(app)

    event = {"id": "evt_async_1", "type": "invoice.paid", "data": {"object": {"id": "in_1"}}}
    resp = client.post("/webhooks/stripe", content=json.dumps(event), headers={"stripe-signature": "sig"})
    assert resp.status_code == 200
    assert resp.json().get("queued") is True
    assert called["sent"] is True
