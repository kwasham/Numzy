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
    interval: str | None = Body(None, embed=True),
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
    if interval and interval not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="Invalid interval")

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
                **({"interval": interval} if interval else {}),
            },
        )
        sentry_metric_inc(
            "stripe.subscription.created_default_incomplete",
            tags={"price_id": price_id, **({"interval": interval} if interval else {})},
        )
        sentry_set_tags({"checkout.interval": interval or "monthly"})
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


@router.post("/subscription/change")
async def change_subscription_plan(
        target_plan: str = Body(..., embed=True),
        interval: str | None = Body(None, embed=True),
        proration_behavior: str | None = Body(None, embed=True),
        defer_downgrade: bool | None = Body(None, embed=True),
        idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
        user: User = Depends(get_user),
        db: AsyncSession = Depends(get_db),
):
    """Change the active subscription's plan (upgrade or downgrade) with explicit proration policy.

    Enhancements:
    - Supports monthly or yearly (interval) mapping (yearly prices optional / environment driven).
    - Provides optional defer_downgrade flag: when True and this is a downgrade, we avoid immediate price swap
      and instead set `cancel_at_period_end=True` so the customer stays on the higher tier until renewal, while
      storing a hint via metadata for reconciliation workers to apply new plan post-period.
    - If proration_behavior not provided we auto-select: upgrades => create_invoice, downgrades => none.
    - NOTE: True scheduling via Subscription Schedules could be implemented later; for now we emulate via
      cancel_at_period_end semantics plus metadata marker `pending_plan`.
    """
    
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")
    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    # Normalize plan & interval
    plan_lower = target_plan.lower()
    valid_plans = {"personal", "pro", "business"}
    if plan_lower not in valid_plans:
        raise HTTPException(status_code=400, detail="Unsupported target_plan")
    if interval is not None and interval not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="Invalid interval; must be monthly or yearly")
    chosen_interval = interval or "monthly"

    customer_id = getattr(user, "stripe_customer_id", None)
    if not customer_id:
        raise HTTPException(status_code=404, detail="No Stripe customer")

    # Fetch current subscription
    try:
        subs = stripe.Subscription.list(customer=customer_id, status="all", limit=2)  # type: ignore
        sub_list = subs.get("data", []) if isinstance(subs, dict) else []
        if not sub_list:
            raise HTTPException(status_code=404, detail="No active subscription")
        current_sub = sub_list[0]
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to fetch subscriptions for change: %s", e)
        raise HTTPException(status_code=500, detail="Unable to load subscription")

    # Determine current plan price id
    current_item = (current_sub.get("items", {}).get("data", []) or [None])[0] if isinstance(current_sub, dict) else None
    current_price_id = current_item and current_item.get("price", {}).get("id")

    # Map plan + interval -> price id (fall back to monthly when yearly not configured)
    plan_to_price = {
        ("personal", "monthly"): getattr(settings, "STRIPE_PRICE_PERSONAL_MONTHLY", None),
        ("personal", "yearly"): getattr(settings, "STRIPE_PRICE_PERSONAL_YEARLY", None),
        ("pro", "monthly"): getattr(settings, "STRIPE_PRICE_PRO_MONTHLY", None),
        ("pro", "yearly"): getattr(settings, "STRIPE_PRICE_PRO_YEARLY", None),
        ("business", "monthly"): getattr(settings, "STRIPE_PRICE_BUSINESS_MONTHLY", getattr(settings, "STRIPE_PRICE_TEAM_MONTHLY", None)),
        ("business", "yearly"): getattr(settings, "STRIPE_PRICE_BUSINESS_YEARLY", None),
    }
    new_price_id = plan_to_price.get((plan_lower, chosen_interval)) or plan_to_price.get((plan_lower, "monthly"))
    if not new_price_id:
        raise HTTPException(status_code=400, detail="Price not configured for target plan")
    if new_price_id == current_price_id:
        return {"ok": True, "unchanged": True, "subscription_id": current_sub.get("id")}

    # Infer upgrade vs downgrade. Normalize yearly amounts to monthly equivalent for comparison
    # so an interval switch monthly->yearly (with discount) does not appear as a massive upgrade.
    def _price_info(price_id):
        try:
            pr = stripe.Price.retrieve(price_id)  # type: ignore
            unit_amount = pr.get("unit_amount") or 0
            recurring = pr.get("recurring") or {}
            interval = recurring.get("interval")  # 'month' | 'year' | None
            interval_count = recurring.get("interval_count") or 1
            return unit_amount, interval, interval_count
        except Exception:
            return 0, None, 1

    cur_amount_raw, cur_interval, cur_interval_count = _price_info(current_price_id) if current_price_id else (0, None, 1)
    new_amount_raw, new_interval, new_interval_count = _price_info(new_price_id)

    def _normalized(unit_amount, interval, interval_count):
        # Normalize to monthly amount in cents for fair comparison
        if interval == "year":
            # Divide by 12 * interval_count (usually 1) to get per-month equivalent
            return unit_amount / (12 * (interval_count or 1))
        if interval == "month":
            return unit_amount / (interval_count or 1)
        return unit_amount  # fallback

    current_amount_norm = _normalized(cur_amount_raw, cur_interval, cur_interval_count)
    new_amount_norm = _normalized(new_amount_raw, new_interval, new_interval_count)
    is_upgrade = new_amount_norm > current_amount_norm

    # Decide proration behavior
    if proration_behavior and proration_behavior not in {"create_invoice", "none"}:
        raise HTTPException(status_code=400, detail="Invalid proration_behavior")
    effective_behavior = proration_behavior or ("create_invoice" if is_upgrade else "none")

    sub_id = current_sub.get("id")
    request_opts = {}
    if idempotency_key:
        request_opts["idempotency_key"] = idempotency_key

    try:
        pending_plan = None
        metadata_update = {}
        downgrade_scheduled = False
        # Detect same-plan interval switch (e.g., pro monthly -> pro yearly) to force immediate price swap
        user_current_plan = getattr(user, "plan", None)
        current_plan_name = None
        try:
            if user_current_plan is not None:
                current_plan_name = user_current_plan.value.lower()
        except Exception:
            current_plan_name = None
        same_plan_interval_switch = current_plan_name == plan_lower and current_price_id != new_price_id

        if (not same_plan_interval_switch
                and not is_upgrade
                and effective_behavior == "none"
                and (defer_downgrade or defer_downgrade is None)):
            pending_plan = plan_lower
            metadata_update["pending_plan"] = pending_plan
            downgrade_scheduled = True
            updated = stripe.Subscription.modify(  # type: ignore
                sub_id,
                cancel_at_period_end=True,
                metadata={**(current_sub.get("metadata") or {}), **metadata_update},
                **request_opts,
            )
        else:
            updated = stripe.Subscription.modify(  # type: ignore
                sub_id,
                items=[{"id": current_item.get("id"), "price": new_price_id}],
                proration_behavior=("create_invoice" if is_upgrade else "none"),
                cancel_at_period_end=False,
                metadata={**(current_sub.get("metadata") or {}), **metadata_update},
                **request_opts,
            )
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to modify subscription %s: %s", sub_id, e)
        try:
            sentry_metric_inc(
                "stripe.subscription.change.error",
                tags={
                    "plan": plan_lower,
                    "interval": chosen_interval,
                    "upgrade": str(is_upgrade).lower(),
                },
            )
            sentry_breadcrumb(
                category="stripe",
                message="subscription.change.error",
                data={
                    "subscription_id": sub_id,
                    "from_price": current_price_id,
                    "to_price": new_price_id,
                    "error": str(e),
                },
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Failed to change plan")

    # Update local plan optimistically (webhooks will reconcile authoritative state)
    try:
        if plan_lower == "personal":
            user.plan = PlanType.PERSONAL  # type: ignore
        elif plan_lower == "pro":
            user.plan = PlanType.PRO  # type: ignore
        elif plan_lower == "business":
            user.plan = PlanType.BUSINESS
        await db.commit()
    except Exception:  # pragma: no cover
        await db.rollback()

    # Observability
    try:
        sentry_breadcrumb(
            category="stripe",
            message="subscription.plan.changed",
            data={
                "subscription_id": sub_id,
                "from_price": current_price_id,
                "to_price": new_price_id,
                "is_upgrade": is_upgrade,
                "proration_behavior": effective_behavior,
                "deferred": bool(not is_upgrade and effective_behavior == "none" and (defer_downgrade or defer_downgrade is None)),
            },
        )
        sentry_metric_inc(
            "stripe.subscription.plan.changed",
            tags={
                "upgrade": str(is_upgrade).lower(),
                "proration": effective_behavior,
                "plan": plan_lower,
                "from_to": f"{current_price_id or 'none'}->{new_price_id}",
            },
        )
        sentry_metric_inc(
            "stripe.subscription.change",
            tags={
                "upgrade": str(is_upgrade).lower(),
                "plan": plan_lower,
                "interval": chosen_interval,
                "deferred": str(not is_upgrade and effective_behavior == "none" and (defer_downgrade or defer_downgrade is None)).lower(),
            },
        )
        if locals().get('downgrade_scheduled'):
            sentry_metric_inc(
                "stripe.subscription.downgrade_scheduled",
                tags={"plan": plan_lower, "interval": chosen_interval},
            )
    except Exception:
        pass

    return {
        "ok": True,
        "subscription_id": sub_id,
        "plan": plan_lower,
        "interval": chosen_interval,
        "upgrade": is_upgrade,
        "proration_behavior": effective_behavior,
        "deferred": bool(not is_upgrade and effective_behavior == "none" and (defer_downgrade or defer_downgrade is None)),
        "stripe_status": updated.get("status") if isinstance(updated, dict) else None,
    }
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")
    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    # Normalize plan & interval
    plan_lower = target_plan.lower()
    valid_plans = {"personal", "pro", "business"}
    if plan_lower not in valid_plans:
        raise HTTPException(status_code=400, detail="Unsupported target_plan")
    if interval is not None and interval not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="Invalid interval; must be monthly or yearly")
    chosen_interval = interval or "monthly"

    customer_id = getattr(user, "stripe_customer_id", None)
    if not customer_id:
        raise HTTPException(status_code=404, detail="No Stripe customer")

    # Fetch current subscription
    try:
        subs = stripe.Subscription.list(customer=customer_id, status="all", limit=2)  # type: ignore
        sub_list = subs.get("data", []) if isinstance(subs, dict) else []
        if not sub_list:
            raise HTTPException(status_code=404, detail="No active subscription")
        current_sub = sub_list[0]
    except HTTPException:
        raise
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to fetch subscriptions for change: %s", e)
        raise HTTPException(status_code=500, detail="Unable to load subscription")

    # Determine current plan price id
    current_item = (current_sub.get("items", {}).get("data", []) or [None])[0] if isinstance(current_sub, dict) else None
    current_price_id = current_item and current_item.get("price", {}).get("id")

    # Map plan + interval -> price id (fall back to monthly when yearly not configured)
    plan_to_price = {
        ("personal", "monthly"): getattr(settings, "STRIPE_PRICE_PERSONAL_MONTHLY", None),
        ("personal", "yearly"): getattr(settings, "STRIPE_PRICE_PERSONAL_YEARLY", None),
        ("pro", "monthly"): getattr(settings, "STRIPE_PRICE_PRO_MONTHLY", None),
        ("pro", "yearly"): getattr(settings, "STRIPE_PRICE_PRO_YEARLY", None),
        ("business", "monthly"): getattr(settings, "STRIPE_PRICE_BUSINESS_MONTHLY", getattr(settings, "STRIPE_PRICE_TEAM_MONTHLY", None)),
        ("business", "yearly"): getattr(settings, "STRIPE_PRICE_BUSINESS_YEARLY", None),
    }
    new_price_id = plan_to_price.get((plan_lower, chosen_interval)) or plan_to_price.get((plan_lower, "monthly"))
    if not new_price_id:
        raise HTTPException(status_code=400, detail="Price not configured for target plan")
    if new_price_id == current_price_id:
        return {"ok": True, "unchanged": True, "subscription_id": current_sub.get("id")}

    # Infer upgrade vs downgrade from monthly amount
    def _amount(price_id):
        try:
            pr = stripe.Price.retrieve(price_id)  # type: ignore
            return pr.get("unit_amount") or 0
        except Exception:
            return 0

    current_amount = _amount(current_price_id) if current_price_id else 0
    new_amount = _amount(new_price_id)
    is_upgrade = new_amount > current_amount

    # Decide proration behavior
    # If caller provided override, trust (validated subset); else choose based on upgrade/downgrade policy
    if proration_behavior and proration_behavior not in {"create_invoice", "none"}:
        raise HTTPException(status_code=400, detail="Invalid proration_behavior")
    effective_behavior = proration_behavior or ("create_invoice" if is_upgrade else "none")

    # Build subscription modification: replace first item price
    sub_id = current_sub.get("id")
    request_opts = {}
    if idempotency_key:
        request_opts["idempotency_key"] = idempotency_key

    try:
        pending_plan = None
        metadata_update = {}
        if not is_upgrade and effective_behavior == "none" and (defer_downgrade or defer_downgrade is None):
            # Defer downgrade: keep current price until renewal, set cancel_at_period_end=True + mark pending plan
            pending_plan = plan_lower
            metadata_update["pending_plan"] = pending_plan
            updated = stripe.Subscription.modify(  # type: ignore
                sub_id,
                cancel_at_period_end=True,
                metadata={**(current_sub.get("metadata") or {}), **metadata_update},
                **request_opts,
            )
        else:
            # Immediate application (upgrade or forced immediate downgrade)
            updated = stripe.Subscription.modify(  # type: ignore
                sub_id,
                items=[{"id": current_item.get("id"), "price": new_price_id}],
                proration_behavior=("create_invoice" if is_upgrade else "none"),
                cancel_at_period_end=False,
                metadata={**(current_sub.get("metadata") or {}), **metadata_update},
                **request_opts,
            )
    except Exception as e:  # pragma: no cover
        logger.exception("Failed to modify subscription %s: %s", sub_id, e)
        raise HTTPException(status_code=500, detail="Failed to change plan")

    # Update local plan optimistically (webhooks will reconcile authoritative state)
    try:
        if plan_lower == "personal":
            user.plan = PlanType.PERSONAL  # type: ignore
        elif plan_lower == "pro":
            user.plan = PlanType.PRO  # type: ignore
        elif plan_lower == "business":
            user.plan = PlanType.BUSINESS
        await db.commit()
    except Exception:  # pragma: no cover
        await db.rollback()

    # Observability
    try:
        sentry_breadcrumb(
            category="stripe",
            message="subscription.plan.changed",
            data={
                "subscription_id": sub_id,
                "from_price": current_price_id,
                "to_price": new_price_id,
                "is_upgrade": is_upgrade,
                "proration_behavior": effective_behavior,
            },
        )
        sentry_metric_inc(
            "stripe.subscription.plan.changed",
            tags={
                "upgrade": str(is_upgrade).lower(),
                "proration": effective_behavior,
                "plan": plan_lower,
            },
        )
    except Exception:
        pass

    return {
        "ok": True,
        "subscription_id": sub_id,
        "plan": plan_lower,
        "interval": chosen_interval,
        "upgrade": is_upgrade,
        "proration_behavior": effective_behavior,
        "deferred": bool(not is_upgrade and effective_behavior == "none" and (defer_downgrade or defer_downgrade is None)),
        "stripe_status": updated.get("status") if isinstance(updated, dict) else None,
    }


@router.post("/subscription/preview")
async def preview_subscription_change(
    target_plan: str = Body(..., embed=True),
    interval: str | None = Body(None, embed=True),
    user: User = Depends(get_user),
):
    """Preview financial impact of changing to a target plan & interval.

    Returns: { current_amount, new_amount, difference, is_upgrade, currency, interval }
    Falls back gracefully if Stripe errors; values may be zero in failure cases.
    """
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")
    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    plan_lower = target_plan.lower()
    if plan_lower not in {"personal", "pro", "business"}:
        raise HTTPException(status_code=400, detail="Unsupported target_plan")
    if interval is not None and interval not in ("monthly", "yearly"):
        raise HTTPException(status_code=400, detail="Invalid interval")
    chosen_interval = interval or "monthly"

    customer_id = getattr(user, "stripe_customer_id", None)
    if not customer_id:
        raise HTTPException(status_code=404, detail="No Stripe customer")
    try:
        subs = stripe.Subscription.list(customer=customer_id, status="all", limit=1)  # type: ignore
        sub_list = subs.get("data", []) if isinstance(subs, dict) else []
        current_sub = sub_list[0] if sub_list else None
    except Exception:
        current_sub = None
    current_item = (current_sub.get("items", {}).get("data", []) or [None])[0] if isinstance(current_sub, dict) else None
    current_price_id = current_item and current_item.get("price", {}).get("id")

    plan_to_price = {
        ("personal", "monthly"): getattr(settings, "STRIPE_PRICE_PERSONAL_MONTHLY", None),
        ("personal", "yearly"): getattr(settings, "STRIPE_PRICE_PERSONAL_YEARLY", None),
        ("pro", "monthly"): getattr(settings, "STRIPE_PRICE_PRO_MONTHLY", None),
        ("pro", "yearly"): getattr(settings, "STRIPE_PRICE_PRO_YEARLY", None),
        ("business", "monthly"): getattr(settings, "STRIPE_PRICE_BUSINESS_MONTHLY", getattr(settings, "STRIPE_PRICE_TEAM_MONTHLY", None)),
        ("business", "yearly"): getattr(settings, "STRIPE_PRICE_BUSINESS_YEARLY", None),
    }
    new_price_id = plan_to_price.get((plan_lower, chosen_interval)) or plan_to_price.get((plan_lower, "monthly"))
    if not new_price_id:
        raise HTTPException(status_code=400, detail="Price not configured for target plan")

    def _amt(price_id: str | None):
        if not price_id:
            return 0, "USD"
        try:
            pr = stripe.Price.retrieve(price_id)  # type: ignore
            return (pr.get("unit_amount") or 0) / 100.0, (pr.get("currency") or "usd").upper()
        except Exception:
            return 0, "USD"

    cur_amount, cur_currency = _amt(current_price_id)
    new_amount, new_currency = _amt(new_price_id)
    currency = new_currency or cur_currency
    difference = round(new_amount - cur_amount, 2)
    is_upgrade = difference > 0
    try:
        sentry_breadcrumb(
            category="stripe",
            message="subscription.preview",
            data={
                "from_price_id": current_price_id,
                "to_price_id": new_price_id,
                "difference": difference,
                "upgrade": is_upgrade,
                "plan": plan_lower,
                "interval": chosen_interval,
            },
        )
        sentry_metric_inc(
            "stripe.subscription.preview",
            tags={
                "plan": plan_lower,
                "interval": chosen_interval,
                "upgrade": str(is_upgrade).lower(),
            },
        )
    except Exception:
        pass
    return {
        "current_amount": cur_amount,
        "new_amount": new_amount,
        "difference": difference,
        "is_upgrade": is_upgrade,
        "currency": currency,
        "interval": chosen_interval,
    }


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
                    "pending_plan": (sub.get("metadata", {}) or {}).get("pending_plan"),
                    "cancel_at_period_end": sub.get("cancel_at_period_end"),
                }
        except Exception as e:  # pragma: no cover
            logger.warning("Stripe subscription lookup failed for customer %s: %s", customer_id, e)

    # Normalize plan to string for the frontend
    plan_value = getattr(user, "plan", PlanType.FREE)
    if isinstance(plan_value, PlanType):
        plan_value = plan_value.value

    # Build a catalog of plans with monthly (& yearly when available) prices.
    # Shape: { planId: { name, currency, monthly: { price, price_id }, yearly?: { price, price_id } } }
    catalog = {
        "free": {"name": "Free", "currency": "USD", "monthly": {"price": 0, "price_id": None}},
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

        personal_monthly = _resolve_price_by_lookup(getattr(settings, "STRIPE_LOOKUP_PERSONAL_MONTHLY", None))
        if personal_monthly:
            unit = personal_monthly.get("unit_amount") or 0
            currency = (personal_monthly.get("currency") or "usd").upper()
            catalog["personal"] = {
                "name": "Personal",
                "currency": currency,
                "monthly": {"price": float(unit) / 100.0, "price_id": personal_monthly.get("id")},
            }

        pro_monthly = _resolve_price_by_lookup(getattr(settings, "STRIPE_LOOKUP_PRO_MONTHLY", None)) or (
            stripe.Price.retrieve(settings.STRIPE_PRICE_PRO_MONTHLY) if settings.STRIPE_PRICE_PRO_MONTHLY else None  # type: ignore
        )
        pro_yearly = _resolve_price_by_lookup(getattr(settings, "STRIPE_LOOKUP_PRO_YEARLY", None)) or (
            stripe.Price.retrieve(settings.STRIPE_PRICE_PRO_YEARLY) if settings.STRIPE_PRICE_PRO_YEARLY else None  # type: ignore
        )
        if pro_monthly:
            unit = pro_monthly.get("unit_amount") or 0
            currency = (pro_monthly.get("currency") or "usd").upper()
            catalog["pro"] = {
                "name": "Pro",
                "currency": currency,
                "monthly": {"price": float(unit) / 100.0, "price_id": pro_monthly.get("id")},
            }
            if pro_yearly and (pro_yearly.get("currency") or "usd").upper() == currency:
                y_unit = pro_yearly.get("unit_amount") or 0
                catalog["pro"]["yearly"] = {"price": float(y_unit) / 100.0, "price_id": pro_yearly.get("id")}

        business_monthly = _resolve_price_by_lookup(getattr(settings, "STRIPE_LOOKUP_BUSINESS_MONTHLY", None)) or (
            stripe.Price.retrieve(settings.STRIPE_PRICE_BUSINESS_MONTHLY) if settings.STRIPE_PRICE_BUSINESS_MONTHLY else None  # type: ignore
        )
        # (Optional) yearly business lookup variables could be added in config later
        if business_monthly:
            unit = business_monthly.get("unit_amount") or 0
            currency = (business_monthly.get("currency") or "usd").upper()
            catalog["business"] = {
                "name": "Business",
                "currency": currency,
                "monthly": {"price": float(unit) / 100.0, "price_id": business_monthly.get("id")},
            }
    except Exception as e:  # pragma: no cover
        logger.warning("Failed to build plan catalog from Stripe: %s", e)

    # Reconcile plan based on active subscription price if it doesn't match DB
    try:
        target_plan: PlanType | None = None
        if sub_price_id:
            # Direct match against env IDs (fallback)
            if sub_price_id == settings.STRIPE_PRICE_PERSONAL_MONTHLY:
                target_plan = PlanType.PERSONAL
            elif sub_price_id == settings.STRIPE_PRICE_PRO_MONTHLY or sub_price_id == settings.STRIPE_PRICE_PRO_YEARLY:
                target_plan = PlanType.PRO
            elif sub_price_id == settings.STRIPE_PRICE_BUSINESS_MONTHLY or sub_price_id == settings.STRIPE_PRICE_TEAM_MONTHLY:
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
                    if lk and lk in (settings.STRIPE_LOOKUP_PERSONAL_MONTHLY,):
                        target_plan = PlanType.PERSONAL
                    elif lk and lk in (settings.STRIPE_LOOKUP_PRO_MONTHLY, settings.STRIPE_LOOKUP_PRO_YEARLY):
                        target_plan = PlanType.PRO
                    elif lk and lk in (settings.STRIPE_LOOKUP_BUSINESS_MONTHLY, settings.STRIPE_LOOKUP_TEAM_MONTHLY):
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
            "payment_state": getattr(user, "payment_state", None) or payment_state or (subscription_summary.get("status") if subscription_summary else None),
            "subscription_status": getattr(user, "subscription_status", None) or (subscription_summary.get("status") if subscription_summary else None),
            "last_invoice_status": getattr(user, "last_invoice_status", None),
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

@router.post("/address")
async def update_billing_address(
    line1: str = Body(..., embed=True),
    city: str | None = Body(None, embed=True),
    state: str | None = Body(None, embed=True),
    postal_code: str | None = Body(None, embed=True),
    country: str | None = Body(None, embed=True),
    line2: str | None = Body(None, embed=True),
    user: User = Depends(get_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist user billing address locally and (best‑effort) sync to Stripe Customer.

    Returns stored address. Minimal validation; rely on Stripe for deeper checks.
    """
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe not configured")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_API_KEY")
    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore

    # Persist to DB
    user.billing_address_line1 = line1
    user.billing_address_line2 = line2
    user.billing_address_city = city
    user.billing_address_state = state
    user.billing_address_postal_code = postal_code
    user.billing_address_country = country
    try:
        await db.commit()
    except Exception as e:  # pragma: no cover
        await db.rollback()
        logger.exception("Failed to persist billing address: %s", e)
        raise HTTPException(status_code=500, detail="Failed to save address")

    # Ensure Stripe customer exists (best effort)
    customer_id = getattr(user, "stripe_customer_id", None)
    if not customer_id:
        try:
            found = stripe.Customer.list(email=user.email, limit=1)  # type: ignore
            data = found.get("data", []) if isinstance(found, dict) else []
            if data:
                customer_id = data[0]["id"]
                user.stripe_customer_id = customer_id
                await db.commit()
            else:
                cust = stripe.Customer.create(email=user.email)  # type: ignore
                customer_id = cust["id"]
                user.stripe_customer_id = customer_id
                await db.commit()
        except Exception:  # pragma: no cover
            customer_id = None

    # Sync to Stripe (best effort; ignore failures so UX remains smooth)
    if customer_id:
        try:
            stripe.Customer.modify(  # type: ignore
                customer_id,
                address={
                    "line1": line1,
                    **({"line2": line2} if line2 else {}),
                    **({"city": city} if city else {}),
                    **({"state": state} if state else {}),
                    **({"postal_code": postal_code} if postal_code else {}),
                    **({"country": country} if country else {}),
                },
            )
        except Exception as e:  # pragma: no cover
            logger.warning("Stripe customer address update failed for %s: %s", customer_id, e)

    # Observability (non‑PII)
    try:
        sentry_breadcrumb(
            category="stripe",
            message="customer.address.updated",
            data={"customer_id": customer_id, "country": country},
        )
        sentry_metric_inc("stripe.customer.address.updated", tags={"country": country or "unknown"})
    except Exception:
        pass

    return {
        "ok": True,
        "address": {
            "line1": line1,
            "line2": line2,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "country": country,
        },
        "stripe_customer_id": customer_id,
    }
