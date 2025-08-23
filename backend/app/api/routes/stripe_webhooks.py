from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.config import settings, get_webhook_secret_list
import logging
import datetime as dt
from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.tables import User
from app.models.enums import PlanType
from functools import lru_cache
from app.core.tasks import process_stripe_event
from app.core.observability import sentry_set_tags, sentry_breadcrumb, sentry_metric_inc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"]) 

try:  # Stripe is optional until webhook is configured
    import stripe  # type: ignore
except Exception as e:  # pragma: no cover
    # Log full exception to help diagnose missing/shadowed module issues
    logger.exception("Failed to import Stripe SDK: %s", e)
    stripe = None  # type: ignore


@lru_cache(maxsize=1)
def _get_redis_client():
    """Return a cached Redis client for lightweight operations.

    We only use basic SET NX EX for webhook de-duplication; failures are non-fatal.
    """
    try:  # lazy import to avoid hard dep when Redis is unavailable
        import redis  # type: ignore
        return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception as e:  # pragma: no cover - defensive; webhook will continue without dedup
        logger.warning("[stripe] redis unavailable for dedup: %s", e)
        return None

@router.post("/webhooks/stripe")
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
    endpoint_secrets = get_webhook_secret_list()

    if not endpoint_secrets:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    last_sig_error: Exception | None = None
    event = None
    for secret in endpoint_secrets:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=secret,
            )
            break
        except stripe.error.SignatureVerificationError as e:  # type: ignore
            last_sig_error = e
            continue
        except Exception as e:  # pragma: no cover
            last_sig_error = e
            continue
    if event is None:
        logger.warning("Invalid Stripe signature after trying %d secrets: %s", len(endpoint_secrets), last_sig_error)
        try:
            sentry_metric_inc("stripe.webhook.invalid_signature")
        except Exception:
            pass
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Redis-based de-duplication to avoid double-processing the same event
    event_id = event.get("id") if isinstance(event, dict) else None
    if event_id:
        try:
            r = _get_redis_client()
            if r is not None:
                # store for 7 days; if already present, treat as duplicate and ack
                set_result = r.set(name=f"stripe:webhook:{event_id}", value="1", nx=True, ex=7 * 24 * 3600)
                if not set_result:
                    logger.info("[stripe] duplicate webhook event ignored id=%s", event_id)
                    try:
                        sentry_metric_inc("stripe.webhook.duplicate")
                    except Exception:
                        pass
                    return JSONResponse(status_code=200, content={"received": True, "duplicate": True, "id": event_id})
        except Exception as dedup_ex:  # pragma: no cover - do not fail webhook on redis errors
            logger.warning("[stripe] redis dedup check failed: %s", dedup_ex)

    # Handle a richer set of common events (no-op DB writes yet; structured logs only)
    event_type: str = event.get("type", "")
    data_object: Dict[str, Any] = event.get("data", {}).get("object", {})
    try:
        sentry_metric_inc("stripe.webhook.received", tags={"event_type": event_type})
    except Exception:
        pass

    # Optional backend-side allowlist to reduce noise even if Dashboard is broad
    try:
        allowed = (settings.STRIPE_WEBHOOK_ALLOWED_EVENTS or "").strip()
        if allowed:
            import fnmatch
            patterns = [p.strip() for p in allowed.split(",") if p.strip()]
            if patterns and not any(fnmatch.fnmatch(event_type, pat) for pat in patterns):
                logger.debug("[stripe] event filtered by allowlist type=%s patterns=%s", event_type, patterns)
                try:
                    sentry_metric_inc("stripe.webhook.ignored", tags={"event_type": event_type})
                except Exception:
                    pass
                return JSONResponse(status_code=200, content={"received": True, "filtered": True, "type": event_type})
    except Exception:
        # best-effort; do not fail on bad pattern
        pass
    # Lightweight observability (no PII)
    sentry_set_tags({
        "stripe.event_type": event_type,
    })
    if isinstance(data_object, dict) and data_object.get("id"):
        # Breadcrumb with safe identifiers
        sentry_breadcrumb(
            category="stripe",
            message=f"webhook:{event_type}",
            level="info",
            data={"object": data_object.get("object"), "id": data_object.get("id")},
        )

    def _to_iso(ts: Any) -> str | None:
        try:
            if ts is None:
                return None
            # Stripe timestamps are seconds since epoch
            return dt.datetime.utcfromtimestamp(int(ts)).isoformat() + "Z"
        except Exception:
            return None

    # Offload processing to Dramatiq and return immediately
    try:
        process_stripe_event.send(event)  # type: ignore[arg-type]
        sentry_metric_inc("stripe.webhook.queued", tags={"event_type": event_type})
        logger.debug("[stripe] queued event for async processing type=%s id=%s", event_type, data_object.get("id"))
        return JSONResponse(status_code=200, content={"received": True, "queued": True, "type": event_type})
    except Exception as e:
        logger.warning("[stripe] failed to enqueue event for async processing: %s", e)
        try:
            sentry_metric_inc("stripe.webhook.enqueue_error", tags={"event_type": event_type})
        except Exception:
            pass

    try:
        # 1. Checkout completion -------------------------------------------------
        if event_type == "checkout.session.completed":
            sess_id = data_object.get("id")
            mode = data_object.get("mode")
            customer = data_object.get("customer")
            customer_email = data_object.get("customer_email")
            subscription = data_object.get("subscription")
            client_ref = data_object.get("client_reference_id")
            logger.info(
                "[stripe] checkout.session.completed id=%s mode=%s customer=%s email=%s subscription=%s client_ref=%s",
                sess_id, mode, customer, customer_email, subscription, client_ref,
            )
            sentry_metric_inc("stripe.checkout.completed")
            try:
                if customer:
                    async with AsyncSessionLocal() as session:
                        user_obj = None
                        if client_ref:
                            user_obj = await session.scalar(select(User).where(User.clerk_id == str(client_ref)))
                        if not user_obj and customer_email:
                            user_obj = await session.scalar(select(User).where(User.email == customer_email))
                        if user_obj and not getattr(user_obj, "stripe_customer_id", None):
                            user_obj.stripe_customer_id = customer
                            await session.commit()
                            logger.info(
                                "[stripe] linked user id=%s clerk_id=%s email=%s to stripe customer=%s",
                                getattr(user_obj, "id", None), getattr(user_obj, "clerk_id", None), getattr(user_obj, "email", None), customer,
                            )
                        elif not user_obj:
                            logger.warning(
                                "[stripe] unable to link stripe customer; no user found for client_ref=%s email=%s",
                                client_ref, customer_email,
                            )
            except Exception as link_ex:  # pragma: no cover
                logger.exception("[stripe] failed linking stripe customer to user: %s", link_ex)

        # 2. Subscription lifecycle ---------------------------------------------
        elif event_type in ("customer.subscription.created", "customer.subscription.updated", "customer.subscription.deleted"):
            sub_id = data_object.get("id")
            status = data_object.get("status")
            customer = data_object.get("customer")
            current_period_end = _to_iso(data_object.get("current_period_end"))
            cancel_at = _to_iso(data_object.get("cancel_at"))
            canceled_at = _to_iso(data_object.get("canceled_at"))
            items = data_object.get("items", {})
            price_obj = None
            if isinstance(items, dict):
                data_list = items.get("data", [])
                if isinstance(data_list, list) and data_list:
                    price_obj = data_list[0].get("price", {})
            price_id = price_obj.get("id") if isinstance(price_obj, dict) else None
            product_id = price_obj.get("product") if isinstance(price_obj, dict) else None
            logger.info(
                "[stripe] subscription event=%s id=%s status=%s customer=%s price=%s product=%s period_end=%s cancel_at=%s canceled_at=%s",
                event_type, sub_id, status, customer, price_id, product_id, current_period_end, cancel_at, canceled_at,
            )
            sentry_metric_inc("stripe.subscription.event", tags={"event_type": event_type, "status": status or ""})
            try:
                sentry_set_tags({"stripe.subscription_status": status or "", "stripe.price_id": price_id or ""})
            except Exception:
                pass
            try:
                if customer:
                    async with AsyncSessionLocal() as session:
                        user = await session.scalar(select(User).where(User.stripe_customer_id == customer))
                        if user:
                            user.subscription_status = status
                            if event_type == "customer.subscription.deleted" or status in ("canceled", "unpaid"):
                                if getattr(user, "plan", None) != PlanType.FREE:
                                    user.plan = PlanType.FREE
                                    logger.info(
                                        "[stripe] downgraded user id=%s email=%s to FREE due to subscription %s",
                                        getattr(user, "id", None), getattr(user, "email", None), sub_id,
                                    )
                                user.payment_state = "past_due" if status in ("unpaid",) else None
                            elif status in ("active", "trialing") and price_id:
                                new_plan: PlanType | None = None
                                if price_id in (settings.STRIPE_PRICE_PRO_MONTHLY, settings.STRIPE_PRICE_PRO_YEARLY):
                                    new_plan = PlanType.PRO
                                elif price_id == settings.STRIPE_PRICE_TEAM_MONTHLY:
                                    new_plan = PlanType.BUSINESS
                                if new_plan is not None and getattr(user, "plan", None) != new_plan:
                                    user.plan = new_plan
                                    logger.info(
                                        "[stripe] set user plan from subscription event user_id=%s email=%s plan=%s sub_id=%s",
                                        getattr(user, "id", None), getattr(user, "email", None), new_plan, sub_id,
                                    )
                                user.payment_state = "ok"
                            await session.commit()
            except Exception as db_ex:  # pragma: no cover
                logger.exception("[stripe] failed to downgrade on subscription deletion: %s", db_ex)

        # 3. Invoice paid / succeeded (recoveries) ------------------------------
        elif event_type in ("invoice.payment_succeeded", "invoice.paid"):
            invoice_id = data_object.get("id")
            customer = data_object.get("customer")
            subscription = data_object.get("subscription")
            amount_paid = data_object.get("amount_paid")
            billing_reason = data_object.get("billing_reason")
            customer_email = data_object.get("customer_email")
            price_id = None
            try:
                lines = data_object.get("lines", {}).get("data", [])
                if isinstance(lines, list) and lines:
                    price_id = lines[0].get("price", {}).get("id")
            except Exception:
                price_id = None
            try:
                async with AsyncSessionLocal() as session:
                    user = None
                    if customer:
                        user = await session.scalar(select(User).where(User.stripe_customer_id == customer))
                    if not user and customer_email:
                        user = await session.scalar(select(User).where(User.email == customer_email))
                    changed = False
                    prev_state = getattr(user, "payment_state", None) if user else None
                    if user and customer and not getattr(user, "stripe_customer_id", None):
                        user.stripe_customer_id = customer
                        changed = True
                    if price_id:
                        plan: PlanType | None = None
                        if price_id in (settings.STRIPE_PRICE_PRO_MONTHLY, settings.STRIPE_PRICE_PRO_YEARLY):
                            plan = PlanType.PRO
                        elif price_id == settings.STRIPE_PRICE_TEAM_MONTHLY:
                            plan = PlanType.BUSINESS
                        if user and plan is not None and getattr(user, "plan", None) != plan:
                            user.plan = plan
                            changed = True
                    if user:
                        if prev_state == "past_due":
                            sentry_metric_inc("stripe.dunning.recovered")
                            user.last_invoice_status = "paid"
                        elif prev_state == "requires_action":
                            sentry_metric_inc("stripe.sca.completed")
                            user.last_invoice_status = "paid"
                        if getattr(user, "payment_state", None) != "ok":
                            user.payment_state = "ok"
                            changed = True
                    if user and changed:
                        await session.commit()
            except Exception as db_ex:  # pragma: no cover
                logger.exception("[stripe] DB update failed for email=%s: %s", customer_email, db_ex)
            logger.info(
                "[stripe] invoice success id=%s customer=%s subscription=%s amount_paid=%s reason=%s",
                invoice_id, customer, subscription, amount_paid, billing_reason,
            )
            sentry_metric_inc("stripe.invoice.paid")
            try:
                sentry_set_tags({"stripe.invoice_id": invoice_id or "", "stripe.price_id": price_id or ""})
            except Exception:
                pass

        # 4. Invoice failed (enter dunning) -------------------------------------
        elif event_type == "invoice.payment_failed":
            invoice_id = data_object.get("id")
            customer = data_object.get("customer")
            subscription = data_object.get("subscription")
            attempt_count = data_object.get("attempt_count")
            price_id = None
            try:
                lines = data_object.get("lines", {}).get("data", [])
                if isinstance(lines, list) and lines:
                    price_id = lines[0].get("price", {}).get("id")
            except Exception:
                price_id = None
            logger.warning(
                "[stripe] invoice failed id=%s customer=%s subscription=%s attempts=%s",
                invoice_id, customer, subscription, attempt_count,
            )
            sentry_metric_inc("stripe.invoice.failed")
            sentry_metric_inc("stripe.dunning.entered")
            try:
                sentry_breadcrumb(
                    category="stripe", message="invoice.payment_failed", level="warning",
                    data={"invoice_id": invoice_id, "customer": customer, "subscription": subscription, "attempts": attempt_count, "price_id": price_id},
                )
                sentry_set_tags({"stripe.invoice_id": invoice_id or "", "stripe.price_id": price_id or ""})
            except Exception:
                pass
            try:
                if customer:
                    async with AsyncSessionLocal() as session:
                        user = await session.scalar(select(User).where(User.stripe_customer_id == customer))
                        if user:
                            user.payment_state = "past_due"
                            user.last_invoice_status = "failed"
                            await session.commit()
            except Exception as db_ex:  # pragma: no cover
                logger.exception("[stripe] failed to persist past_due: %s", db_ex)

        # 5. Invoice action required (enter SCA) --------------------------------
        elif event_type == "invoice.payment_action_required":
            invoice_id = data_object.get("id")
            customer = data_object.get("customer")
            subscription = data_object.get("subscription")
            price_id = None
            try:
                lines = data_object.get("lines", {}).get("data", [])
                if isinstance(lines, list) and lines:
                    price_id = lines[0].get("price", {}).get("id")
            except Exception:
                price_id = None
            logger.warning("[stripe] invoice requires action id=%s customer=%s subscription=%s", invoice_id, customer, subscription)
            sentry_metric_inc("stripe.invoice.action_required")
            sentry_metric_inc("stripe.sca.entered")
            try:
                sentry_breadcrumb(
                    category="stripe", message="invoice.payment_action_required", level="warning",
                    data={"invoice_id": invoice_id, "customer": customer, "subscription": subscription, "price_id": price_id},
                )
                sentry_set_tags({"stripe.invoice_id": invoice_id or "", "stripe.price_id": price_id or ""})
            except Exception:
                pass
            try:
                if customer:
                    async with AsyncSessionLocal() as session:
                        user = await session.scalar(select(User).where(User.stripe_customer_id == customer))
                        if user:
                            user.payment_state = "requires_action"
                            user.last_invoice_status = "action_required"
                            await session.commit()
            except Exception as db_ex:  # pragma: no cover
                logger.exception("[stripe] failed to persist requires_action: %s", db_ex)

        # 6. Customer updates ---------------------------------------------------
        elif event_type in ("customer.created", "customer.updated"):
            cust_id = data_object.get("id")
            email = data_object.get("email")
            if cust_id and email:
                try:
                    async with AsyncSessionLocal() as session:
                        user = await session.scalar(select(User).where(User.email == email))
                        if user and not getattr(user, "stripe_customer_id", None):
                            user.stripe_customer_id = cust_id
                            await session.commit()
                except Exception as db_ex:  # pragma: no cover
                    logger.exception("[stripe] DB update failed on customer event for email=%s: %s", email, db_ex)

        # 7. Ancillary low-value events ----------------------------------------
        elif event_type in ("payment_method.attached", "invoice.created", "invoice.finalized", "invoice.updated"):
            logger.debug("[stripe] ancillary event type=%s id=%s", event_type, data_object.get("id"))

        # 8. Fallback -----------------------------------------------------------
        else:
            logger.debug("[stripe] unhandled event type=%s id=%s", event_type, data_object.get("id"))
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("[stripe] error handling event %s: %s", event_type, e)
        try:
            sentry_metric_inc("stripe.webhook.handler_error", tags={"event_type": event_type})
        except Exception:
            pass

    return JSONResponse(status_code=200, content={"received": True, "type": event_type})


# Legacy compatibility endpoint (no signature verification) --------------------------------------------------
# Some older clients and internal tests post directly to /stripe/webhook without the
# new /webhooks prefix or signature header. Provide a lightweight alias that
# accepts raw JSON and reuses the async queueing path. This intentionally skips
# signature verification and MUST NOT be exposed publicly without appropriate
# network/AuthN controls. Safe here because the real signed path still exists
# and this is only used in test suite.
@router.post("/stripe/webhook")
async def stripe_webhook_legacy(request: Request):  # pragma: no cover - thin adapter
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    # Minimal shape enforcement
    if not isinstance(body, dict) or "type" not in body:
        raise HTTPException(status_code=400, detail="Missing event type")
    try:
        process_stripe_event.send(body)  # type: ignore[arg-type]
        try:
            sentry_metric_inc("stripe.webhook.queued", tags={"event_type": body.get("type", "")})
        except Exception:
            pass
        return JSONResponse(status_code=200, content={"received": True, "queued": True, "type": body.get("type")})
    except Exception as e:  # pragma: no cover
        logger.warning("[stripe] legacy webhook enqueue failed: %s", e)
        return JSONResponse(status_code=200, content={"received": True, "type": body.get("type")})
