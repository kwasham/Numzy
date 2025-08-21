from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends, Body, Header
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

# Observability helpers (best-effort; no-ops when Sentry/DSN unavailable)
from app.core.observability import (
    sentry_breadcrumb,
    sentry_metric_inc,
    sentry_set_tags,
)

try:
    import stripe  # type: ignore
except Exception as e:  # pragma: no cover
    stripe = None  # type: ignore
    logging.getLogger(__name__).exception("Stripe SDK not available: %s", e)


@router.post("/checkout")
async def create_checkout_session(
    price_id: str | None = Body(None, embed=True),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
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
        # Build request options including optional idempotency key
        request_opts = {}
        if idempotency_key:
            request_opts["idempotency_key"] = idempotency_key
        # Optional automatic tax
        automatic_tax = {"enabled": True} if getattr(settings, "STRIPE_AUTOMATIC_TAX_ENABLED", False) else None
        session = stripe.checkout.Session.create(  # type: ignore
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": chosen_price, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=getattr(user, "clerk_id", None),
            allow_promotion_codes=True,
            billing_address_collection="auto",
            **({"automatic_tax": automatic_tax} if automatic_tax else {}),
            **request_opts,
        )
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to create checkout session: %s", e)
        raise HTTPException(status_code=500, detail="Unable to create checkout session")

    # Observability (non-PII)
    try:
        sentry_breadcrumb(
            category="stripe",
            message="checkout.session.created",
            data={
                "price_id": chosen_price,
                "customer_id": customer_id,
                "session_id": session.get("id"),
            },
        )
        sentry_metric_inc("stripe.checkout.session.created", tags={"price_id": chosen_price})
    except Exception:
        pass

    return JSONResponse({"url": session["url"]})


@router.post("/elements/init")
async def init_elements_subscription(
    price_id: str = Body(..., embed=True),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_user),
):
    """Initialize a subscription for a custom checkout using Stripe Elements.

    Creates a subscription in default_incomplete state and returns the latest invoice
    payment_intent client_secret so the client can confirm with Stripe Elements.
    """
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")

    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    if not price_id:
        raise HTTPException(status_code=400, detail="price_id is required")

    # Ensure Stripe customer exists for user
    customer_id = getattr(user, "stripe_customer_id", None)
    if not customer_id:
        try:
            # Try lookup by email first
            found = stripe.Customer.list(email=user.email, limit=1)  # type: ignore
            data = found.get("data", []) if isinstance(found, dict) else []
            if data:
                customer_id = data[0]["id"]
            else:
                cust = stripe.Customer.create(email=user.email)  # type: ignore
                customer_id = cust["id"]
            user.stripe_customer_id = customer_id
            await db.commit()
        except Exception as e:  # pragma: no cover
            logger.exception("Failed to ensure Stripe customer for Elements init: %s", e)
            raise HTTPException(status_code=500, detail="Unable to initialize customer")

    try:
        request_opts = {}
        if idempotency_key:
            request_opts["idempotency_key"] = idempotency_key
        automatic_tax = {"enabled": True} if getattr(settings, "STRIPE_AUTOMATIC_TAX_ENABLED", False) else None
        sub = stripe.Subscription.create(  # type: ignore
            customer=customer_id,
            items=[{"price": price_id}],
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
            metadata={"user_id": str(getattr(user, "id", "")), "clerk_id": getattr(user, "clerk_id", None) or ""},
            payment_settings={"save_default_payment_method": "on_subscription"},
            **({"automatic_tax": automatic_tax} if automatic_tax else {}),
            **request_opts,
        )
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to create default_incomplete subscription: %s", e)
        raise HTTPException(status_code=500, detail="Unable to create subscription")

    try:
        latest_invoice = sub.get("latest_invoice", {}) if isinstance(sub, dict) else {}
        pi = latest_invoice.get("payment_intent", {}) if isinstance(latest_invoice, dict) else {}
        client_secret = pi.get("client_secret")
        if not client_secret:
            raise ValueError("Missing client_secret on payment_intent")
    except Exception as e:  # pragma: no cover
        logger.exception("Subscription created but no client_secret available: %s", e)
        raise HTTPException(status_code=500, detail="Failed to initialize payment")

    # Observability (non-PII)
    try:
        sentry_breadcrumb(
            category="stripe",
            message="subscription.created_default_incomplete",
            data={
                "price_id": price_id,
                "customer_id": customer_id,
                "subscription_id": sub.get("id"),
            },
        )
        sentry_metric_inc("stripe.subscription.created_default_incomplete", tags={"price_id": price_id})
    except Exception:
        pass

    return JSONResponse(
        {
            "subscription_id": sub.get("id"),
            "client_secret": client_secret,
            "customer_id": customer_id,
        }
    )


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
        portal_params = {
            "customer": customer_id,
            "return_url": f"{settings.FRONTEND_BASE_URL}/dashboard",
        }
        if getattr(settings, "STRIPE_PORTAL_CONFIGURATION_ID", None):
            portal_params["configuration"] = settings.STRIPE_PORTAL_CONFIGURATION_ID
        session = stripe.billing_portal.Session.create(  # type: ignore
            **portal_params
        )
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to create billing portal session: %s", e)
        raise HTTPException(status_code=500, detail="Unable to create billing portal session")

    # Observability (non-PII)
    try:
        sentry_breadcrumb(
            category="stripe",
            message="billing_portal.session.created",
            data={
                "customer_id": customer_id,
                "session_id": session.get("id"),
            },
        )
        sentry_metric_inc("stripe.billing_portal.session.created")
    except Exception:
        pass

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
    sub_price_id = None
    payment_state: str | None = None
    action_meta: dict | None = None  # minimal info to drive client prompts
    if customer_id:
        try:
            # Fetch most recent subscription; try to expand latest invoice/payment intent for action states
            subs = stripe.Subscription.list(  # type: ignore
                customer=customer_id,
                status="all",
                limit=1,
                expand=["data.latest_invoice.payment_intent"],
            )
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
                sub_price_id = price_id
                period_end = None
                try:
                    cpe = sub.get("current_period_end")
                    if cpe:
                        import datetime as _dt
                        period_end = _dt.datetime.fromtimestamp(int(cpe), _dt.UTC).isoformat().replace("+00:00", "Z")
                except Exception:
                    period_end = None

                # Determine payment state
                try:
                    sub_status = (sub.get("status") or "").lower()
                    if sub_status in ("past_due", "unpaid"):
                        payment_state = "past_due"
                    else:
                        # Inspect latest invoice payment_intent if expanded
                        latest_invoice = sub.get("latest_invoice") or {}
                        pi = latest_invoice.get("payment_intent") if isinstance(latest_invoice, dict) else None
                        pi_status = (pi.get("status") or "").lower() if isinstance(pi, dict) else ""
                        if pi_status in ("requires_action", "requires_payment_method"):
                            payment_state = "requires_action"
                            action_meta = {
                                "invoice_id": latest_invoice.get("id") if isinstance(latest_invoice, dict) else None,
                                "payment_intent_id": pi.get("id") if isinstance(pi, dict) else None,
                            }
                        else:
                            payment_state = "ok"
                except Exception:
                    payment_state = payment_state or None

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

    # Build a lightweight catalog of plans with current Stripe prices (prefer lookup keys)
    catalog = {
        "startup": {"name": "Startup", "currency": "USD", "price": 0, "price_id": None},
    }
    try:
        def _resolve_price_by_lookup(lookup_key: str | None) -> dict | None:
            if not lookup_key:
                return None
            try:
                prices = stripe.Price.list(lookup_keys=[lookup_key], active=True, limit=1)  # type: ignore
                data = prices.get("data", []) if isinstance(prices, dict) else []
                return data[0] if data else None
            except Exception:
                return None

        pro_price = _resolve_price_by_lookup(getattr(settings, "STRIPE_LOOKUP_PRO_MONTHLY", None))
        if not pro_price and settings.STRIPE_PRICE_PRO_MONTHLY:
            pro_price = stripe.Price.retrieve(settings.STRIPE_PRICE_PRO_MONTHLY)  # type: ignore
        if pro_price:
            unit = pro_price.get("unit_amount") or 0
            currency = (pro_price.get("currency") or "usd").upper()
            catalog["standard"] = {
                "name": "Standard",
                "currency": currency,
                "price": float(unit) / 100.0,
                "price_id": pro_price.get("id"),
            }

        team_price = _resolve_price_by_lookup(getattr(settings, "STRIPE_LOOKUP_TEAM_MONTHLY", None))
        if not team_price and settings.STRIPE_PRICE_TEAM_MONTHLY:
            team_price = stripe.Price.retrieve(settings.STRIPE_PRICE_TEAM_MONTHLY)  # type: ignore
        if team_price:
            unit = team_price.get("unit_amount") or 0
            currency = (team_price.get("currency") or "usd").upper()
            catalog["business"] = {
                "name": "Business",
                "currency": currency,
                "price": float(unit) / 100.0,
                "price_id": team_price.get("id"),
            }
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to build plan catalog from Stripe: %s", e)

    # Reconcile plan based on active subscription price if it doesn't match DB
    try:
        target_plan: PlanType | None = None
        if sub_price_id:
            # Direct match against env IDs (fallback)
            if sub_price_id == settings.STRIPE_PRICE_PRO_MONTHLY or sub_price_id == settings.STRIPE_PRICE_PRO_YEARLY:
                target_plan = PlanType.PRO
            elif sub_price_id == settings.STRIPE_PRICE_TEAM_MONTHLY:
                target_plan = PlanType.BUSINESS
            # If lookup keys configured, try to resolve and map
            if target_plan is None and any([
                getattr(settings, "STRIPE_LOOKUP_PRO_MONTHLY", None),
                getattr(settings, "STRIPE_LOOKUP_PRO_YEARLY", None),
                getattr(settings, "STRIPE_LOOKUP_TEAM_MONTHLY", None),
            ]):
                try:
                    pr = stripe.Price.retrieve(sub_price_id)  # type: ignore
                    lk = pr.get("lookup_key")
                    if lk and lk in (settings.STRIPE_LOOKUP_PRO_MONTHLY, settings.STRIPE_LOOKUP_PRO_YEARLY):
                        target_plan = PlanType.PRO
                    elif lk and lk in (settings.STRIPE_LOOKUP_TEAM_MONTHLY,):
                        target_plan = PlanType.BUSINESS
                except Exception:
                    pass
        if target_plan is not None and getattr(user, "plan", None) != target_plan:
            user.plan = target_plan
            await db.commit()
            # Normalize for response
            plan_value = target_plan.value
    except Exception as _recon_ex:  # pragma: no cover
        logger.warning("Failed to reconcile user plan from subscription: %s", _recon_ex)

    # Observability: annotate current billing state (non-PII)
    try:
        sentry_set_tags({
            "billing.plan": str(plan_value),
            "billing.payment_state": str(payment_state or ""),
            "billing.subscription_status": str((subscription_summary or {}).get("status")),
        })
    except Exception:
        pass

    return JSONResponse(
        {
            "plan": plan_value,
            "stripe_customer_id": customer_id,
            "subscription": subscription_summary,
            "payment_state": payment_state or (subscription_summary.get("status") if subscription_summary else None),
            "action": action_meta,
            "catalog": catalog,
        }
    )


@router.get("/payment-intent")
async def get_payment_intent_client_secret(
    subscription_id: str | None = None,
    invoice_id: str | None = None,
):
    """Return client_secret for the latest invoice payment intent for recovery flows.

    Either provide subscription_id (preferred) to expand latest_invoice.payment_intent,
    or provide invoice_id to retrieve its payment_intent.
    """
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")

    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    try:
        client_secret = None
        if subscription_id:
            sub = stripe.Subscription.retrieve(  # type: ignore
                subscription_id,
                expand=["latest_invoice.payment_intent"],
            )
            inv = sub.get("latest_invoice", {}) if isinstance(sub, dict) else {}
            pi = inv.get("payment_intent", {}) if isinstance(inv, dict) else {}
            client_secret = pi.get("client_secret")
        elif invoice_id:
            inv = stripe.Invoice.retrieve(  # type: ignore
                invoice_id,
                expand=["payment_intent"],
            )
            pi = inv.get("payment_intent", {}) if isinstance(inv, dict) else {}
            client_secret = pi.get("client_secret")
        else:
            raise HTTPException(status_code=400, detail="subscription_id or invoice_id is required")
        if not client_secret:
            raise HTTPException(status_code=404, detail="No client_secret available")
        return JSONResponse({"client_secret": client_secret})
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to retrieve payment intent client_secret: %s", e)
        raise HTTPException(status_code=500, detail="Unable to retrieve payment intent")

    # If we reached here, we returned earlier. For completeness, add a breadcrumb before returns above.


@router.post("/subscription/payment-method")
async def update_subscription_payment_method(
    subscription_id: str = Body(..., embed=True),
    payment_method_id: str = Body(..., embed=True),
    invoice_id: str | None = Body(None, embed=True),
    user: User = Depends(get_user),
):
    """Attach a PaymentMethod to the customer and set it as the subscription default.

    Optionally attempts to pay a specific invoice after updating the default PM.
    """
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")

    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    try:
        # Retrieve subscription to get the customer id
        sub = stripe.Subscription.retrieve(subscription_id)  # type: ignore
        customer_id = sub.get("customer") if isinstance(sub, dict) else None
        if not customer_id:
            raise HTTPException(status_code=404, detail="Subscription not found")

        # Ensure the payment method is attached to the customer
        try:
            pm = stripe.PaymentMethod.retrieve(payment_method_id)  # type: ignore
            pm_customer = pm.get("customer") if isinstance(pm, dict) else None
            if not pm_customer:
                stripe.PaymentMethod.attach(payment_method_id, customer=customer_id)  # type: ignore
        except Exception as e:  # pragma: no cover
            logger.exception("Failed to attach payment method %s: %s", payment_method_id, e)
            raise HTTPException(status_code=400, detail="Invalid or unattached payment method")

        # Set as default for the subscription
        stripe.Subscription.modify(  # type: ignore
            subscription_id,
            default_payment_method=payment_method_id,
        )

        # Best-effort: if an invoice is provided, attempt to pay it now
        paid_invoice = None
        if invoice_id:
            try:
                paid_invoice = stripe.Invoice.pay(invoice_id)  # type: ignore
            except Exception as e:  # pragma: no cover
                logger.warning("Attempt to pay invoice %s failed: %s", invoice_id, e)

        # Observability (non-PII)
        try:
            sentry_breadcrumb(
                category="stripe",
                message="subscription.payment_method.updated",
                data={
                    "subscription_id": subscription_id,
                    "invoice_id": invoice_id,
                    "paid": bool(paid_invoice and isinstance(paid_invoice, dict) and paid_invoice.get("paid")),
                },
            )
            sentry_metric_inc(
                "stripe.subscription.payment_method.updated",
                tags={"paid_invoice": str(bool(paid_invoice and isinstance(paid_invoice, dict) and paid_invoice.get("paid")))},
            )
        except Exception:
            pass

        return JSONResponse({
            "ok": True,
            "subscription_id": subscription_id,
            "payment_method_id": payment_method_id,
            "invoice_paid": bool(paid_invoice and isinstance(paid_invoice, dict) and paid_invoice.get("paid")),
        })
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to update subscription payment method: %s", e)
        raise HTTPException(status_code=500, detail="Unable to update payment method")
