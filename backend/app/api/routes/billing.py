from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.tables import User
from app.api.dependencies import get_user
from app.models.enums import PlanType

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

try:
    import stripe  # type: ignore
except Exception as e:  # pragma: no cover
    stripe = None  # type: ignore
    logging.getLogger(__name__).exception("Stripe SDK not available: %s", e)


@router.post("/checkout")
async def create_checkout_session(
    price_id: str | None = Body(None, embed=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user),
):
    """Create a Stripe Checkout Session for the authenticated user.

    Prefers existing user.stripe_customer_id, otherwise creates a Stripe customer
    and backfills the ID. Client reference id is set to the Clerk id for linkage.
    """
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")

    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    # Choose price: prefer request body, fallback to configured PRO monthly
    chosen_price = price_id or settings.STRIPE_PRICE_PRO_MONTHLY
    if not chosen_price:
        raise HTTPException(status_code=400, detail="Missing price_id and no default configured")

    # Ensure we have a customer for this user
    customer_id = getattr(user, "stripe_customer_id", None)
    if not customer_id:
        try:
            cust = stripe.Customer.create(email=user.email)  # type: ignore
            customer_id = cust["id"]
            user.stripe_customer_id = customer_id
            await db.commit()
        except Exception as e:  # pragma: no cover
            logger.exception("Failed to create Stripe customer: %s", e)
            raise HTTPException(status_code=500, detail="Unable to create customer")

    success_url = f"{settings.FRONTEND_BASE_URL}/dashboard?checkout=success"
    cancel_url = f"{settings.FRONTEND_BASE_URL}/pricing?checkout=cancelled"

    try:
        session = stripe.checkout.Session.create(  # type: ignore
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": chosen_price, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=getattr(user, "clerk_id", None),
            allow_promotion_codes=True,
            billing_address_collection="auto",
        )
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to create checkout session: %s", e)
        raise HTTPException(status_code=500, detail="Unable to create checkout session")

    return JSONResponse({"url": session["url"]})


@router.post("/portal")
async def create_billing_portal_session(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user),
):
    """Create a Stripe Billing Portal session for the authenticated user."""
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")

    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    customer_id = getattr(user, "stripe_customer_id", None)
    if not customer_id:
        # Try to find existing Stripe customer by email first
        try:
            found = stripe.Customer.list(email=user.email, limit=1)  # type: ignore
            data = found.get("data", []) if isinstance(found, dict) else []
            if data:
                customer_id = data[0]["id"]
                user.stripe_customer_id = customer_id
                await db.commit()
        except Exception as e:  # pragma: no cover
            logger.warning("Stripe customer search by email failed for %s: %s", user.email, e)
        if not customer_id:
            # Best-effort: create customer and backfill to allow managing billing details
            try:
                cust = stripe.Customer.create(email=user.email)  # type: ignore
                customer_id = cust["id"]
                user.stripe_customer_id = customer_id
                await db.commit()
            except Exception as e:  # pragma: no cover
                logger.exception("Failed to create Stripe customer for %s: %s", user.email, e)
                raise HTTPException(status_code=500, detail="Unable to initialize billing portal")

    try:
        session = stripe.billing_portal.Session.create(  # type: ignore
            customer=customer_id,
            return_url=f"{settings.FRONTEND_BASE_URL}/dashboard",
        )
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to create billing portal session: %s", e)
        raise HTTPException(status_code=500, detail="Unable to create billing portal session")

    return JSONResponse({"url": session["url"]})


@router.get("/status")
async def get_billing_status(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user),
):
    """Return the current user's plan and Stripe subscription status.

    - Attempts to ensure we know the stripe_customer_id by looking up by email.
    - If a customer exists, fetch the most recent subscription and summarize its status.
    """
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")

    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    customer_id = getattr(user, "stripe_customer_id", None)
    # Best-effort: try to locate existing customer by email
    if not customer_id and user.email:
        try:
            found = stripe.Customer.list(email=user.email, limit=1)  # type: ignore
            data = found.get("data", []) if isinstance(found, dict) else []
            if data:
                customer_id = data[0]["id"]
                user.stripe_customer_id = customer_id
                await db.commit()
        except Exception as e:  # pragma: no cover
            logger.warning("Stripe customer lookup failed for %s: %s", user.email, e)

    subscription_summary = None
    if customer_id:
        try:
            subs = stripe.Subscription.list(customer=customer_id, status="all", limit=1)  # type: ignore
            subs_data = subs.get("data", []) if isinstance(subs, dict) else []
            if subs_data:
                sub = subs_data[0]
                price_id = None
                try:
                    items = sub.get("items", {}).get("data", [])
                    if items:
                        price_id = items[0].get("price", {}).get("id")
                except Exception:
                    price_id = None
                period_end = None
                try:
                    cpe = sub.get("current_period_end")
                    if cpe:
                        import datetime as _dt
                        period_end = _dt.datetime.utcfromtimestamp(int(cpe)).isoformat() + "Z"
                except Exception:
                    period_end = None
                subscription_summary = {
                    "id": sub.get("id"),
                    "status": sub.get("status"),
                    "price_id": price_id,
                    "current_period_end": period_end,
                }
        except Exception as e:  # pragma: no cover
            logger.warning("Stripe subscription lookup failed for customer %s: %s", customer_id, e)

    # Normalize plan to string for the frontend
    plan_value = getattr(user, "plan", PlanType.FREE)
    if isinstance(plan_value, PlanType):
        plan_value = plan_value.value

    return JSONResponse(
        {
            "plan": plan_value,
            "stripe_customer_id": customer_id,
            "subscription": subscription_summary,
        }
    )
