from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"]) 

try:  # Stripe is optional until webhook is configured
    import stripe  # type: ignore
except Exception:  # pragma: no cover
    stripe = None  # type: ignore


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events.

    Verifies the Stripe-Signature header using STRIPE_WEBHOOK_SECRET.
    Responds 200 OK for recognized events, 400 for signature errors.
    """
    if stripe is None:
        logger.error("Stripe SDK not installed; cannot process webhooks")
        raise HTTPException(status_code=500, detail="Stripe SDK not available")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    if not endpoint_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=endpoint_secret,
        )
    except stripe.error.SignatureVerificationError as e:  # type: ignore
        logger.warning("Invalid Stripe signature: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:  # pragma: no cover
        logger.exception("Error parsing Stripe webhook: %s", e)
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Handle a subset of common events; extend as needed
    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "invoice.payment_succeeded":
        # Update subscription status/usage if needed
        logger.info("Invoice succeeded for customer %s", data_object.get("customer"))
    elif event_type == "customer.subscription.updated":
        logger.info("Subscription updated: %s", data_object.get("id"))
    elif event_type == "customer.subscription.deleted":
        logger.info("Subscription canceled: %s", data_object.get("id"))
    else:
        logger.debug("Unhandled Stripe event: %s", event_type)

    return JSONResponse(status_code=200, content={"received": True})
