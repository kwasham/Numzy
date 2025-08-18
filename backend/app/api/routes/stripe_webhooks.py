from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.config import settings
import logging
import datetime as dt
from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.tables import User
from app.models.enums import PlanType
from functools import lru_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"]) 

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
                    return JSONResponse(status_code=200, content={"received": True, "duplicate": True, "id": event_id})
        except Exception as dedup_ex:  # pragma: no cover - do not fail webhook on redis errors
            logger.warning("[stripe] redis dedup check failed: %s", dedup_ex)

    # Handle a richer set of common events (no-op DB writes yet; structured logs only)
    event_type: str = event.get("type", "")
    data_object: Dict[str, Any] = event.get("data", {}).get("object", {})

    def _to_iso(ts: Any) -> str | None:
        try:
            if ts is None:
                return None
            # Stripe timestamps are seconds since epoch
            return dt.datetime.utcfromtimestamp(int(ts)).isoformat() + "Z"
        except Exception:
            return None

    try:
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
            # Persist stripe_customer_id on the user when we can safely associate it.
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

        elif event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
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

            # If subscription was deleted or set to canceled, downgrade user to FREE
            try:
                if customer and (event_type == "customer.subscription.deleted" or status in ("canceled", "unpaid")):
                    async with AsyncSessionLocal() as session:
                        user = await session.scalar(select(User).where(User.stripe_customer_id == customer))
                        if user and getattr(user, "plan", None) != PlanType.FREE:
                            user.plan = PlanType.FREE
                            await session.commit()
                            logger.info(
                                "[stripe] downgraded user id=%s email=%s to FREE due to subscription %s",
                                getattr(user, "id", None), getattr(user, "email", None), sub_id,
                            )
                # For created/updated active subscriptions, map plan based on price_id
                elif customer and status in ("active", "trialing") and price_id:
                    async with AsyncSessionLocal() as session:
                        user = await session.scalar(select(User).where(User.stripe_customer_id == customer))
                        if user:
                            new_plan: PlanType | None = None
                            if price_id == settings.STRIPE_PRICE_PRO_MONTHLY or price_id == settings.STRIPE_PRICE_PRO_YEARLY:
                                new_plan = PlanType.PRO
                            elif price_id == settings.STRIPE_PRICE_TEAM_MONTHLY:
                                new_plan = PlanType.BUSINESS
                            if new_plan is not None and getattr(user, "plan", None) != new_plan:
                                user.plan = new_plan
                                await session.commit()
                                logger.info(
                                    "[stripe] set user plan from subscription event user_id=%s email=%s plan=%s sub_id=%s",
                                    getattr(user, "id", None), getattr(user, "email", None), new_plan, sub_id,
                                )
            except Exception as db_ex:  # pragma: no cover
                logger.exception("[stripe] failed to downgrade on subscription deletion: %s", db_ex)

        elif event_type in ("invoice.payment_succeeded", "invoice.paid"):
            invoice_id = data_object.get("id")
            customer = data_object.get("customer")
            subscription = data_object.get("subscription")
            amount_paid = data_object.get("amount_paid")
            billing_reason = data_object.get("billing_reason")
            customer_email = data_object.get("customer_email")

            # Extract price_id if present to map plan
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
                    # Backfill stripe_customer_id if we matched by email
                    if user and customer and not getattr(user, "stripe_customer_id", None):
                        user.stripe_customer_id = customer
                        changed = True
                        logger.info(
                            "[stripe] backfilled stripe_customer_id for user_id=%s email=%s customer=%s via invoice %s",
                            getattr(user, "id", None), getattr(user, "email", None), customer, invoice_id,
                        )

                    # Map plan if price matches configured plans
                    if price_id:
                        plan: PlanType | None = None
                        if price_id == settings.STRIPE_PRICE_PRO_MONTHLY or price_id == settings.STRIPE_PRICE_PRO_YEARLY:
                            plan = PlanType.PRO
                        elif price_id == settings.STRIPE_PRICE_TEAM_MONTHLY:
                            plan = PlanType.BUSINESS
                        if user and plan is not None and getattr(user, "plan", None) != plan:
                            user.plan = plan
                            changed = True
                            logger.info(
                                "[stripe] updated user plan user_id=%s clerk_id=%s email=%s plan=%s via invoice %s",
                                getattr(user, "id", None), getattr(user, "clerk_id", None), getattr(user, "email", None), plan, invoice_id,
                            )

                    if user and changed:
                        await session.commit()
                    elif not user:
                        logger.warning(
                            "[stripe] no user found for invoice (customer=%s, email=%s) to apply updates",
                            customer, customer_email,
                        )
            except Exception as db_ex:  # pragma: no cover
                logger.exception("[stripe] DB update failed for email=%s: %s", customer_email, db_ex)

            logger.info(
                "[stripe] invoice success id=%s customer=%s subscription=%s amount_paid=%s reason=%s",
                invoice_id, customer, subscription, amount_paid, billing_reason,
            )

        elif event_type in ("invoice.payment_failed",):
            invoice_id = data_object.get("id")
            customer = data_object.get("customer")
            subscription = data_object.get("subscription")
            attempt_count = data_object.get("attempt_count")
            logger.warning(
                "[stripe] invoice failed id=%s customer=%s subscription=%s attempts=%s",
                invoice_id, customer, subscription, attempt_count,
            )

        elif event_type in ("customer.created", "customer.updated"):
            # Best-effort backfill on customer events using email
            cust_id = data_object.get("id")
            email = data_object.get("email")
            if cust_id and email:
                try:
                    async with AsyncSessionLocal() as session:
                        user = await session.scalar(select(User).where(User.email == email))
                        if user and not getattr(user, "stripe_customer_id", None):
                            user.stripe_customer_id = cust_id
                            await session.commit()
                            logger.info(
                                "[stripe] linked user by email from customer event user_id=%s email=%s customer=%s",
                                getattr(user, "id", None), email, cust_id,
                            )
                except Exception as db_ex:  # pragma: no cover
                    logger.exception("[stripe] DB update failed on customer event for email=%s: %s", email, db_ex)

        elif event_type in ("payment_method.attached", "invoice.created", "invoice.finalized", "invoice.updated"):
            logger.debug("[stripe] ancillary event type=%s id=%s", event_type, data_object.get("id"))

        else:
            logger.debug("[stripe] unhandled event type=%s id=%s", event_type, data_object.get("id"))
    except Exception as e:  # Defensive: never fail webhook due to handler errors
        logger.exception("[stripe] error handling event %s: %s", event_type, e)

    return JSONResponse(status_code=200, content={"received": True, "type": event_type})
