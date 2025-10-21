from __future__ import annotations

from typing import Any, Dict, List, Optional
import os

from fastapi import APIRouter, Depends, HTTPException, status, Request
import time
from pydantic import BaseModel

try:
    import stripe  # type: ignore
except Exception as e:  # pragma: no cover
    stripe = None  # type: ignore

from app.core.config import settings
from app.api.dependencies import get_user

router = APIRouter(prefix="/issuing", tags=["issuing"])


def _require_stripe():
    if stripe is None:
        raise HTTPException(status_code=500, detail="Stripe SDK not available")
    if not settings.STRIPE_API_KEY:
        raise HTTPException(status_code=500, detail="Stripe API key not configured")
    stripe.api_key = settings.STRIPE_API_KEY  # type: ignore


def _dashboard_base_url() -> str:
    """Return Stripe Dashboard base URL for current environment.

    Priority:
    1) STRIPE_DASHBOARD_BASE_URL if provided (e.g., full sandbox URL)
    2) If STRIPE_ENV == 'sandbox' or API key hints sandbox, use /sandbox
    3) Else if API key looks like test, use /test
    4) Otherwise default to production dashboard
    """
    base = getattr(settings, "STRIPE_DASHBOARD_BASE_URL", None)
    if isinstance(base, str) and base.strip():
        return base.strip().rstrip("/")
    api_key = settings.STRIPE_API_KEY or ""
    stripe_env = os.getenv("STRIPE_ENV", "").lower()
    if stripe_env == "sandbox" or api_key.startswith("sk_sandbox_"):
        return "https://dashboard.stripe.com/sandbox"
    if api_key.startswith("sk_test_"):
        return "https://dashboard.stripe.com/test"
    return "https://dashboard.stripe.com"


def _safe_card_summary(card: Dict[str, Any]) -> Dict[str, Any]:
    ch = card.get("cardholder") or {}
    brand = (card.get("brand") or "").lower() or (card.get("network") or "").lower() or "visa"
    return {
        "id": card.get("id"),
        "brand": brand,
        "last4": card.get("last4"),
        "exp_month": card.get("exp_month"),
        "exp_year": card.get("exp_year"),
        "cardholderName": ch.get("name"),
        "status": card.get("status"),
        "type": card.get("type"),
        "currency": card.get("currency"),
    }


def _requirements_detail_for_card(card_id: str) -> Dict[str, Any]:
    """Gather dashboard links and any past_due requirements for the card's cardholder."""
    details: Dict[str, Any] = {"dashboard_url": f"{_dashboard_base_url()}/issuing/cards/{card_id}"}
    try:
        card = stripe.issuing.Card.retrieve(card_id)  # type: ignore
        ch_id = card.get("cardholder") if isinstance(card.get("cardholder"), str) else card.get("cardholder", {}).get("id")
        if ch_id:
            details["cardholder_dashboard_url"] = f"{_dashboard_base_url()}/issuing/cardholders/{ch_id}"
            ch = stripe.issuing.Cardholder.retrieve(ch_id)  # type: ignore
            reqs = ch.get("requirements") or {}
            past_due = reqs.get("past_due") or []
            if isinstance(past_due, list) and past_due:
                details["past_due"] = past_due
    except Exception:
        # Best-effort
        pass
    return details


def _try_populate_test_cardholder(cardholder_id: str, *, ip: Optional[str] = None, accepted_at: Optional[int] = None) -> None:
    """Best-effort: add common test fields to satisfy cardholder requirements.

    In test mode, providing individual.dob, address, email, and phone is typically
    sufficient to allow activating a virtual card. This function ignores failures.
    """
    try:
        ch = stripe.issuing.Cardholder.retrieve(cardholder_id)  # type: ignore
        name = (ch.get("name") or "Demo User").strip()
        first, last = (name.split(" ", 1) + [""])[:2]
        update_params: Dict[str, Any] = {
            "email": ch.get("email") or "demo@example.com",
            "phone_number": ch.get("phone_number") or "+14155550100",
            "billing": {
                "address": {
                    "line1": "100 Demo Street",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94107",
                    "country": "US",
                }
            },
            "individual": {
                "first_name": first or "Demo",
                "last_name": last or "User",
                "dob": {"day": 1, "month": 1, "year": 1990},
            },
        }
        # If we have client IP/time, attempt to satisfy user_terms_acceptance as well
        ip_val = ip or "127.0.0.1"
        ts_val = accepted_at or int(time.time())
        try:
            update_params["individual"].update({  # type: ignore[index]
                "card_issuing": {"user_terms_acceptance": {"ip": ip_val, "date": ts_val}}
            })
        except Exception:
            pass
        stripe.issuing.Cardholder.modify(cardholder_id, **update_params)  # type: ignore
    except Exception:
        # Best-effort only
        return


def _extract_client_ip(request: Optional[Request]) -> Optional[str]:
    if request is None:
        return None
    try:
        # Prefer X-Forwarded-For (first IP)
        xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
        if xff:
            # Could be comma-separated list
            parts = [p.strip() for p in xff.split(",") if p.strip()]
            if parts:
                return parts[0]
        # Fallback to direct client host
        if request.client and request.client.host:
            return request.client.host
    except Exception:
        return None
    return None


class TestPurchaseRequest(BaseModel):
    amount: int = 500  # cents
    currency: str = "usd"
    merchant_name: Optional[str] = "Test Merchant"
    auto_capture: bool = True


class CreateVirtualCardRequest(BaseModel):
    """Optional inputs when creating a demo virtual card.

    If omitted, we keep permissive defaults suitable for Sandbox/testing.
    """
    currency: Optional[str] = "usd"
    spending_limit_amount: Optional[int] = None  # in minor units; e.g., 5000 => $50
    spending_limit_interval: Optional[str] = None  # 'per_authorization' | 'daily' | 'weekly' | 'monthly' | 'yearly' | 'all_time'
    allowed_categories: Optional[List[str]] = None  # e.g., ["eating_places_restaurants"]
    blocked_categories: Optional[List[str]] = None


def _safe_transaction_summary(txn: Dict[str, Any]) -> Dict[str, Any]:
    card = txn.get("card")
    card_id = card if isinstance(card, str) else (card or {}).get("id")
    merchant = txn.get("merchant_data") or {}
    return {
        "id": txn.get("id"),
        "amount": txn.get("amount"),
        "currency": txn.get("currency"),
        "card_id": card_id,
        "merchant_name": merchant.get("name"),
        "status": txn.get("status"),
        "type": txn.get("type"),
        "created": txn.get("created"),
    }


@router.get("/cards")
async def list_issuing_cards(limit: int = 5, user=Depends(get_user)) -> List[Dict[str, Any]]:
    """
    Return safe summaries of Issuing cards. Does not return PAN/CVC.
    """
    _require_stripe()
    try:
        cards = stripe.issuing.Card.list(limit=min(max(limit, 1), 20))  # type: ignore
        data = cards.get("data", [])
        return [_safe_card_summary(c) for c in data]
    except stripe.error.StripeError as e:  # type: ignore
        raise HTTPException(status_code=400, detail=str(e.user_message or e))


@router.post("/demo/create_virtual_card")
async def create_demo_virtual_card(request: Request, body: Optional[CreateVirtualCardRequest] = None, user=Depends(get_user)) -> Dict[str, Any]:
    """
    Create a demo cardholder and a virtual card for prototyping. Returns safe summary.
    In production, tie cardholder to the authenticated user and collect required KYC/KYB.
    """
    _require_stripe()
    try:
        # Provide fuller test data to satisfy common cardholder requirements in test mode
        full_name = (getattr(user, "name", None) or getattr(user, "email", None) or "Demo User").strip()
        first_name, last_name = (full_name.split(" ", 1) + [""])[:2]
        email = getattr(user, "email", None) or "demo@example.com"

        ch = stripe.issuing.Cardholder.create(  # type: ignore
            name=full_name,
            type="individual",
            email=email,
            phone_number="+14155550100",
            billing={
                "address": {
                    "line1": "100 Demo Street",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94107",
                    "country": "US",
                }
            },
            individual={
                "first_name": first_name or "Demo",
                "last_name": last_name or "User",
                "dob": {"day": 1, "month": 1, "year": 1990},
            },
            metadata={
                "numzy_user_email": email,
            },
        )

        # Create the card and try to set active immediately in test mode
        spending_controls: Dict[str, Any] = {}
        if body:
            # Build spending controls from request inputs (optional)
            if body.allowed_categories:
                spending_controls["allowed_categories"] = body.allowed_categories
            if body.blocked_categories:
                spending_controls["blocked_categories"] = body.blocked_categories
            if body.spending_limit_amount and body.spending_limit_interval:
                spending_controls["spending_limits"] = [
                    {
                        "amount": int(body.spending_limit_amount),
                        "interval": body.spending_limit_interval,
                    }
                ]

        # Default currency
        card_currency = (body.currency if body else None) or "usd"

        create_params: Dict[str, Any] = {
            "type": "virtual",
            "currency": card_currency,
            "cardholder": ch["id"],
            "metadata": {
                "numzy_user_email": email,
            },
        }
        if spending_controls:
            create_params["spending_controls"] = spending_controls

        # Create the card without forcing immediate activation; some programs require additional steps
        card = stripe.issuing.Card.create(**create_params)  # type: ignore
        # Best-effort: populate common test fields and try to activate
        try:
            _try_populate_test_cardholder(ch["id"], ip=_extract_client_ip(request))  # type: ignore[index]
            if card.get("status") != "active":
                try:
                    card = stripe.issuing.Card.modify(card["id"], status="active")  # type: ignore
                except Exception:
                    # Leave as-is; client will handle fix/unfreeze actions
                    pass
        except Exception:
            # Ignore population/activation errors; return the created card
            pass
        return _safe_card_summary(card)
    except stripe.error.StripeError as e:  # type: ignore
        raise HTTPException(status_code=400, detail=str(e.user_message or e))


@router.get("/transactions")
async def list_issuing_transactions(limit: int = 10, user=Depends(get_user)) -> List[Dict[str, Any]]:
    """Return recent Issuing transactions (safe summaries)."""
    _require_stripe()
    try:
        txns = stripe.issuing.Transaction.list(limit=min(max(limit, 1), 50))  # type: ignore
        data = txns.get("data", [])
        return [_safe_transaction_summary(t) for t in data]
    except stripe.error.StripeError as e:  # type: ignore
        raise HTTPException(status_code=400, detail=str(e.user_message or e))


@router.post("/cards/{card_id}/freeze")
async def freeze_card(card_id: str, user=Depends(get_user)) -> Dict[str, Any]:
    _require_stripe()
    try:
        card = stripe.issuing.Card.modify(card_id, status="inactive")  # type: ignore
        return _safe_card_summary(card)
    except stripe.error.StripeError as e:  # type: ignore
        raise HTTPException(status_code=400, detail=str(e.user_message or e))


@router.post("/cards/{card_id}/unfreeze")
async def unfreeze_card(card_id: str, request: Request, user=Depends(get_user)) -> Dict[str, Any]:
    _require_stripe()
    try:
        # Attempt to activate; if cardholder has outstanding requirements, try to populate common test fields
        try:
            card = stripe.issuing.Card.retrieve(card_id)  # type: ignore
            ch_id = card.get("cardholder") if isinstance(card.get("cardholder"), str) else card.get("cardholder", {}).get("id")
            if ch_id:
                _try_populate_test_cardholder(str(ch_id), ip=_extract_client_ip(request))
        except Exception:
            pass
        card = stripe.issuing.Card.modify(card_id, status="active")  # type: ignore
        return _safe_card_summary(card)
    except stripe.error.StripeError as e:  # type: ignore
        details: Dict[str, Any] = {"message": str(e.user_message or e)}
        try:
            details.update(_requirements_detail_for_card(card_id))
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=details)


@router.post("/cards/{card_id}/fix_requirements")
async def fix_requirements(card_id: str, request: Request, user=Depends(get_user)) -> Dict[str, Any]:
    """
    Best-effort populate common test fields on the cardholder and activate the card.
    """
    _require_stripe()
    try:
        card = stripe.issuing.Card.retrieve(card_id)  # type: ignore
        ch_id = card.get("cardholder") if isinstance(card.get("cardholder"), str) else card.get("cardholder", {}).get("id")
        if ch_id:
            _try_populate_test_cardholder(str(ch_id), ip=_extract_client_ip(request))
        card = stripe.issuing.Card.modify(card_id, status="active")  # type: ignore
        return _safe_card_summary(card)
    except stripe.error.StripeError as e:  # type: ignore
        details: Dict[str, Any] = {"message": str(e.user_message or e)}
        try:
            details.update(_requirements_detail_for_card(card_id))
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=details)


@router.get("/cards/{card_id}/requirements")
async def get_cardholder_requirements(card_id: str, user=Depends(get_user)) -> Dict[str, Any]:
    """Return dashboard links and any cardholder requirements.past_due for this card."""
    _require_stripe()
    return _requirements_detail_for_card(card_id)


@router.post("/cards/{card_id}/test_purchase")
async def simulate_test_purchase(card_id: str, body: TestPurchaseRequest, user=Depends(get_user)) -> Dict[str, Any]:
    """
    Simulate an Issuing purchase in test mode using Stripe Test Helpers.
    Creates an authorization for the given amount and optionally captures it.
    Returns a minimal summary including authorization outcome and, if captured, transaction info.
    """
    _require_stripe()
    # Ensure test helpers are available in the installed Stripe SDK
    helpers = getattr(stripe, "test_helpers", None)  # type: ignore[attr-defined]
    if helpers is None or not hasattr(helpers, "issuing"):
        dash_url = f"{_dashboard_base_url()}/issuing/cards/{card_id}"
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Test purchases must be created in the Stripe Dashboard for this account.",
                "dashboard_url": dash_url,
            },
        )
    try:
        # Ensure card is active before simulating purchase; try to activate in test mode
        try:
            card = stripe.issuing.Card.retrieve(card_id)  # type: ignore
            if card.get("status") != "active":
                try:
                    stripe.issuing.Card.modify(card_id, status="active")  # type: ignore
                except Exception:
                    pass
        except Exception:
            pass
        # Create a test authorization using AuthorizationService from test helpers
        issuing_helpers = getattr(helpers, "issuing", None)
        # The Python SDK exposes class-based services under stripe.test_helpers.issuing
        AuthService = getattr(issuing_helpers, "AuthorizationService", None)
        if AuthService is None:
            dash_url = f"{_dashboard_base_url()}/issuing/cards/{card_id}"
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Test purchases must be created in the Stripe Dashboard for this account.",
                    "dashboard_url": dash_url,
                },
            )
        # Use a StripeClient instance; passing a raw string api_key causes 'str' has no attribute 'request'.
        client = stripe.StripeClient(settings.STRIPE_API_KEY)  # type: ignore
        # AuthorizationService expects a requestor-like object; use the client's internal requestor
        auth_service = AuthService(client._requestor)  # type: ignore[attr-defined]
        merchant_data: Dict[str, Any] = {
            "name": body.merchant_name or "Test Merchant",
            # Use a valid category literal for helper enums; fallback will omit if rejected
            "category": "eating_places_restaurants",
            "city": "San Francisco",
            "state": "CA",
            "country": "US",
        }
        try:
            auth = auth_service.create(  # type: ignore
                {
                    "amount": int(body.amount),
                    "currency": body.currency,
                    "card": card_id,
                    "merchant_data": merchant_data,
                }
            )
        except Exception as e:
            # Retry without category if the SDK rejects the value
            msg = str(getattr(e, "user_message", None) or e)
            if "merchant_data[category]" in msg:
                merchant_data.pop("category", None)
                auth = auth_service.create(  # type: ignore
                    {
                        "amount": int(body.amount),
                        "currency": body.currency,
                        "card": card_id,
                        "merchant_data": merchant_data,
                    }
                )
            else:
                raise
        transaction = None
        if body.auto_capture:
            # Capture the authorization to create a transaction
            try:
                transaction = auth_service.capture(  # type: ignore
                    auth["id"],
                    {"capture_amount": int(body.amount)},
                )
            except Exception:
                # If capture isn't available, return auth summary only with dashboard fallback
                transaction = None
        summary: Dict[str, Any] = {
            "authorization_id": auth.get("id"),
            "authorization_status": auth.get("status"),
            "approved": auth.get("approved"),
        }
        if transaction is not None:
            summary.update({
                "transaction_id": transaction.get("id"),
                "transaction_amount": transaction.get("amount"),
                "transaction_currency": transaction.get("currency"),
            })
        return summary
    except stripe.error.StripeError as e:  # type: ignore
        # Common failure reasons: card inactive/frozen, insufficient test funds, disabled issuing
        raise HTTPException(status_code=400, detail=str(e.user_message or e))
    except Exception as e:  # Fallback for non-Stripe exceptions (e.g., bad params/signature)
        dash_url = f"{_dashboard_base_url()}/issuing/cards/{card_id}"
        raise HTTPException(
            status_code=400,
            detail={
                "message": f"Failed to simulate test purchase: {e}",
                "dashboard_url": dash_url,
            },
        )
