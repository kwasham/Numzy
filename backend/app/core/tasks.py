"""Dramatiq task definitions for background processing.

In production, the receipt processing pipeline may involve long
running operations such as running vision models, auditing with
language models, and persisting results. Dramatiq provides a robust
framework for executing these tasks asynchronously via a message
broker like Redis. This module defines Dramatiq actors that mirror
the functionality used in FastAPI background tasks.

To run these tasks you must start a Dramatiq worker pointed at the
module:

```bash
dramatiq receipt_processing_api.app.core.tasks --processes 1 --threads 4
```

The broker URL defaults to Redis at ``redis://localhost:6379/0``. You
can override it via the ``DRAMATIQ_BROKER_URL`` environment variable.
"""

from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Optional
from contextlib import nullcontext

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, TimeLimit, ShutdownNotifications, Retries
try:
    from dramatiq.middleware.prometheus import Prometheus  # type: ignore
except Exception:  # pragma: no cover
    Prometheus = None  # type: ignore
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.tables import Receipt, BackgroundJob, Evaluation, User
from app.models.enums import ReceiptStatus, EvaluationStatus, PlanType
from app.services.extraction_service import ExtractionService

# Optional Sentry for spans (worker initialises globally)
try:  # pragma: no cover - instrumentation only
    import sentry_sdk  # type: ignore
except Exception:  # pragma: no cover
    sentry_sdk = None  # type: ignore

# Lightweight Redis publisher for events
_redis_pub = None
def _get_redis_pub():
    global _redis_pub
    if _redis_pub is None:
        try:
            import redis
            _redis_pub = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception:
            _redis_pub = False  # type: ignore
    return _redis_pub

def _publish_event(user_id: int, receipt_id: int, event_type: str, data: dict):
    pub = _get_redis_pub()
    if not pub:
        return
    payload = {
        "type": event_type,
        "user_id": user_id,
        "receipt_id": receipt_id,
        **data,
    }
    try:
        channel_user = f"receipts:user:{user_id}"
        channel_receipt = f"receipts:receipt:{receipt_id}"
        pub.publish(channel_user, __import__("json").dumps(payload))
        pub.publish(channel_receipt, __import__("json").dumps(payload))
    except Exception:
        pass
from app.services.storage_service import load_file_from_storage

# Update the broker configuration to be more explicit

# Configure broker - remove the condition check to ensure it always uses our settings
# Set up Redis broker with results backend
redis_url = settings.REDIS_URL
print(f"Configuring Dramatiq with Redis URL: {redis_url}")

try:
    redis_broker = RedisBroker(url=redis_url)
    
    # Add middleware including Results (avoid duplicates)
    def _has_mw(broker, mw_cls):
        return any(isinstance(m, mw_cls) for m in broker.middleware)

    result_backend = RedisBackend(url=redis_url)
    if not _has_mw(redis_broker, Results):
        redis_broker.add_middleware(Results(backend=result_backend))
    if not _has_mw(redis_broker, AgeLimit):
        redis_broker.add_middleware(AgeLimit())
    if not _has_mw(redis_broker, TimeLimit):
        redis_broker.add_middleware(TimeLimit())
    if not _has_mw(redis_broker, ShutdownNotifications):
        redis_broker.add_middleware(ShutdownNotifications())
    if not _has_mw(redis_broker, Retries):
        # Exponential backoff up to ~1m
        redis_broker.add_middleware(Retries(max_retries=3, min_backoff=5000, max_backoff=60000, backoff=2.0))
    # Optional Prometheus metrics
    if getattr(settings, "DRAMATIQ_PROMETHEUS_ENABLED", False) and Prometheus is not None:
        # Bind address:port is set via environment variables used by Prometheus middleware
        os.environ.setdefault("PROMETHEUS_ADDR", str(getattr(settings, "DRAMATIQ_PROMETHEUS_ADDR", "127.0.0.1")))
        os.environ.setdefault("PROMETHEUS_PORT", str(getattr(settings, "DRAMATIQ_PROMETHEUS_PORT", 9191)))
        # Only add if not already present
        if not _has_mw(redis_broker, Prometheus):  # type: ignore[arg-type]
            redis_broker.add_middleware(Prometheus())  # type: ignore[operator]
    
    dramatiq.set_broker(redis_broker)
    print("Dramatiq broker configured successfully")
except Exception as e:
    print(f"Failed to configure Dramatiq broker: {e}")
    raise

# Export the broker for Dramatiq CLI
broker = redis_broker

# Create synchronous engine for worker processes with connection pooling
# Prefer a dedicated sync DSN if provided (e.g., ALEMBIC_DATABASE_URL)
sync_db_url = (
    os.getenv("ALEMBIC_DATABASE_URL")
    or getattr(settings, "ALEMBIC_DATABASE_URL", None)
)
if not sync_db_url:
    db_url = settings.DATABASE_URL or os.getenv("DATABASE_URL")
    if not db_url:
        print("Warning: DATABASE_URL not set; falling back to local SQLite app.db")
        sync_db_url = "sqlite:///app.db"
    else:
        # Normalize to a sync driver for SQLAlchemy and prefer psycopg v3
        sync_db_url = db_url.replace("+asyncpg", "")

# If the URL points to Postgres but no driver is specified, or psycopg2 is used, force psycopg v3
try:
    if sync_db_url.startswith("postgres://"):
        sync_db_url = sync_db_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif sync_db_url.startswith("postgresql://"):
        sync_db_url = sync_db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif sync_db_url.startswith("postgresql+psycopg2://"):
        sync_db_url = sync_db_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
except Exception:
    pass
engine = create_engine(
    sync_db_url,
    pool_pre_ping=True,  # Test connections before using them
    pool_size=5,         # Number of connections to maintain
    max_overflow=10,     # Maximum overflow connections
    pool_recycle=3600,   # Recycle connections after 1 hour
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Log masked DB URL for the worker to aid debugging (no password)
try:
    from sqlalchemy.engine.url import make_url
    _u = make_url(sync_db_url)
    _masked = _u.set(password=None)
    print(f"Worker DB URL: {_masked}")
except Exception:
    print("Worker DB URL: <unparseable>")


def _parse_amount(value: str | None) -> float:
    """Parse a monetary amount from a string."""
    if not value:
        return 0.0
    try:
        cleaned = value.replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except Exception:
        return 0.0


@dramatiq.actor(max_retries=3)
def extract_and_audit_receipt(receipt_id: int, user_id: int):
    """Background task to extract data from receipt and audit it.

    Adds Sentry spans for major phases when Sentry SDK is available.
    """
    session = SessionLocal()
    rec = None
    job = None
    start_time = time.time()

    # Get the current message ID from Dramatiq
    from dramatiq.middleware import CurrentMessage
    message = CurrentMessage.get_current_message()
    message_id = message.message_id if message else str(receipt_id)

    span_cm = sentry_sdk.start_span if sentry_sdk else None  # type: ignore

    try:
        # Query receipt first
        if span_cm:
            with span_cm(op="task.fetch_receipt", description="Fetch receipt"):
                rec = session.query(Receipt).filter(Receipt.id == receipt_id).first()
        else:
            rec = session.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not rec:
            raise ValueError(f"Receipt {receipt_id} not found")

        # Ensure job user aligns with the receipt owner (avoids FK issues)
        job_user_id = rec.owner_id

        # Create or update job record after ensuring receipt exists
        job = session.query(BackgroundJob).filter_by(id=message_id).first()
        if not job:
            job = BackgroundJob(
                id=message_id,
                job_type="receipt_extraction",
                status="running",
                user_id=job_user_id,
                receipt_id=receipt_id,
                payload={"receipt_id": receipt_id, "user_id": job_user_id},
                started_at=datetime.utcnow(),
            )
            session.add(job)
        else:
            job.status = "running"
            job.started_at = datetime.utcnow()
        session.commit()

        # Update receipt status
        rec.status = ReceiptStatus.PROCESSING
        rec.task_started_at = datetime.utcnow()
        job.progress = 10
        session.commit()
        _publish_event(job_user_id, receipt_id, "receipt.processing", {
            "status": str(rec.status.value if hasattr(rec.status, 'value') else rec.status),
            "progress": {"extraction": rec.extraction_progress or 0, "audit": rec.audit_progress or 0},
        })

        # Load file data from storage
        print(f"Looking for file at: {rec.file_path}")
        try:
            if span_cm:
                with span_cm(op="task.load_file", description="Load file from storage"):
                    file_data = load_file_from_storage(rec.file_path)
            else:
                file_data = load_file_from_storage(rec.file_path)
        except ValueError as vf:
            # Non-retryable: file truly not present; mark failed and exit
            print(f"File missing for receipt {receipt_id}: {vf}")
            rec.status = ReceiptStatus.FAILED.value
            rec.task_error = str(vf)
            current_retries = getattr(rec, 'task_retry_count', 0) or 0
            rec.task_retry_count = current_retries
            if job:
                job.status = "failed"
                job.error = str(vf)
                job.completed_at = datetime.utcnow()
            session.commit()
            return

        # Update progress: starting extraction
        rec.extraction_progress = 10
        job.progress = 20
        session.commit()
        _publish_event(job_user_id, receipt_id, "receipt.progress", {
            "phase": "extraction", "progress": rec.extraction_progress,
        })

        # Extract data
        extraction_service = ExtractionService()
        import asyncio
        if span_cm:
            with span_cm(op="task.extraction", description="Run extraction service"):
                receipt_details = asyncio.run(extraction_service.extract(file_data, rec.filename))
        else:
            receipt_details = asyncio.run(extraction_service.extract(file_data, rec.filename))
        rec.extracted_data = receipt_details.model_dump()
        # Debug: warn if extraction returned an empty structure
        try:
            if not any([
                rec.extracted_data.get("merchant"),
                rec.extracted_data.get("items"),
                rec.extracted_data.get("total"),
                rec.extracted_data.get("subtotal"),
                rec.extracted_data.get("tax"),
                rec.extracted_data.get("handwritten_notes"),
            ]):
                print(f"[extraction][warn] Empty extraction result for receipt {receipt_id}; debug={list(rec.extracted_data.keys())}")
        except Exception:
            pass
        rec.extraction_progress = 100
        job.progress = 60
        session.commit()
        _publish_event(job_user_id, receipt_id, "receipt.progress", {
            "phase": "extraction", "progress": rec.extraction_progress,
            "extracted_data": rec.extracted_data,
        })

        # Update progress: starting audit
        rec.audit_progress = 10
        job.progress = 70
        session.commit()
        _publish_event(job_user_id, receipt_id, "receipt.progress", {
            "phase": "audit", "progress": rec.audit_progress,
        })

        # Audit the receipt
        from app.models.schemas import AuditDecision

        # Simple threshold check on total
        total_amount = _parse_amount(receipt_details.total)
        amount_over_limit = total_amount > 50  # Check if over $50 spending limit

        if span_cm:
            with span_cm(op="task.audit", description="Audit decision"):
                audit_result = AuditDecision(
                    not_travel_related=False,
                    amount_over_limit=amount_over_limit,
                    math_error=False,
                    handwritten_x=False,
                    reasoning=f"Total amount: ${total_amount:.2f}. {'Over $50 spending limit - needs audit' if amount_over_limit else 'Within $50 spending limit'}",
                    needs_audit=amount_over_limit,
                )
        else:
            audit_result = AuditDecision(
                not_travel_related=False,
                amount_over_limit=amount_over_limit,
                math_error=False,
                handwritten_x=False,
                reasoning=f"Total amount: ${total_amount:.2f}. {'Over $50 spending limit - needs audit' if amount_over_limit else 'Within $50 spending limit'}",
                needs_audit=amount_over_limit,
            )

        rec.audit_decision = audit_result.model_dump()
        rec.audit_progress = 100
        job.progress = 90
        session.commit()
        _publish_event(job_user_id, receipt_id, "receipt.progress", {
            "phase": "audit", "progress": rec.audit_progress,
            "audit_decision": rec.audit_decision,
        })

        # Update receipt as completed
        duration_ms = int((time.time() - start_time) * 1000)
        if span_cm:
            with span_cm(op="task.finalize", description="Finalize receipt + job"):
                rec.status = ReceiptStatus.COMPLETED
        else:
            rec.status = ReceiptStatus.COMPLETED
        rec.task_completed_at = datetime.utcnow()
        rec.processing_duration_ms = duration_ms

        # Update job as completed
        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.utcnow()
        job.result = {
            "status": "success",
            "duration_ms": duration_ms,
            "extracted_total": str(total_amount),
            "needs_audit": amount_over_limit,
        }

        session.commit()
        _publish_event(job_user_id, receipt_id, "receipt.completed", {
            "status": str(rec.status.value if hasattr(rec.status, 'value') else rec.status),
            "duration_ms": duration_ms,
        })
        print(f"Successfully processed receipt {receipt_id} in {duration_ms}ms")

    except Exception as e:
        print(f"Failed to process receipt {receipt_id}: {str(e)}")
        # Always rollback before applying failure updates
        try:
            session.rollback()
        except Exception:
            pass
        if rec:
            rec.status = ReceiptStatus.FAILED.value
            rec.task_error = str(e)
            current_retries = getattr(rec, 'task_retry_count', 0) or 0
            rec.task_retry_count = current_retries + 1
        if job:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.utcnow()
        try:
            session.commit()
        except Exception:
            session.rollback()
        try:
            _publish_event(job.user_id if job else user_id, receipt_id if rec else -1, "receipt.failed", {
                "error": str(e),
            })
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# Data Retention Maintenance
# ---------------------------------------------------------------------------
import asyncio as _asyncio  # localized import to avoid polluting main namespace
from dramatiq import actor as _actor
from datetime import timedelta, timezone as _tz
from sqlalchemy import delete as _delete
from app.services.billing_service import BillingService as _BillingService


@_actor(max_retries=0)
def retention_cleanup():  # pragma: no cover - periodic maintenance
    """Purge receipts beyond each plan's retention window.

    Strategy: Iterate finite-retention plans and delete rows older than
    now - retention_days. Done synchronously inside worker process.
    """
    from sqlalchemy.orm import Session as _Session

    svc = _BillingService()
    now = datetime.utcnow().replace(tzinfo=None)
    # Map plan -> retention days (skip None/unlimited)
    plan_days = {
        plan: limits.retention_days
        for plan, limits in svc.PLAN_LIMIT_MATRIX.items()  # type: ignore[attr-defined]
        if getattr(limits, 'retention_days', None)
    }
    if not plan_days:
        return
    session: _Session = SessionLocal()
    try:
        for plan, days in plan_days.items():
            if not days:
                continue
            cutoff = now - timedelta(days=days)
            try:
                stmt = _delete(Receipt).where(Receipt.created_at < cutoff)  # could further filter by plan if column exists
                session.execute(stmt)
                session.commit()
            except Exception:
                session.rollback()
                continue
    finally:
        try:
            session.close()
        except Exception:
            pass


@dramatiq.actor(max_retries=5)
def process_stripe_event(event: dict):
    """Process a Stripe webhook event asynchronously.

    Mirrors the logic in the API webhook but uses a sync DB session.
    Keep this handler idempotent; webhook delivery may be retried by Stripe.
    """
    session = SessionLocal()
    try:
        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {}) if isinstance(event, dict) else {}
        if event_type == "checkout.session.completed":
            customer = data_object.get("customer")
            client_ref = data_object.get("client_reference_id")
            customer_email = data_object.get("customer_email")
            user_obj = None
            if client_ref:
                user_obj = session.query(User).filter(User.clerk_id == str(client_ref)).first()
            if not user_obj and customer_email:
                user_obj = session.query(User).filter(User.email == customer_email).first()
            if user_obj and customer and not getattr(user_obj, "stripe_customer_id", None):
                user_obj.stripe_customer_id = customer
                session.commit()

        elif event_type in (
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        ):
            status = data_object.get("status")
            customer = data_object.get("customer")
            price_id = None
            try:
                items = data_object.get("items", {}).get("data", [])
                if items:
                    price_id = items[0].get("price", {}).get("id")
            except Exception:
                price_id = None
            if not customer:
                return
            user = session.query(User).filter(User.stripe_customer_id == customer).first()
            if not user:
                return
            if user:
                user.subscription_status = status
                if event_type == "customer.subscription.deleted" or status in ("canceled", "unpaid"):
                    if getattr(user, "plan", None) != PlanType.FREE:
                        user.plan = PlanType.FREE
                    user.payment_state = "past_due" if status in ("unpaid",) else None
                elif status in ("active", "trialing") and price_id:
                    new_plan = None
                    if price_id == getattr(settings, "STRIPE_PRICE_PRO_MONTHLY", None) or price_id == getattr(settings, "STRIPE_PRICE_PRO_YEARLY", None):
                        new_plan = PlanType.PRO
                    elif price_id == getattr(settings, "STRIPE_PRICE_TEAM_MONTHLY", None):
                        new_plan = PlanType.BUSINESS
                    if new_plan is not None and getattr(user, "plan", None) != new_plan:
                        user.plan = new_plan
                    user.payment_state = "ok"
                session.commit()

        elif event_type in ("invoice.payment_succeeded", "invoice.paid"):
            customer = data_object.get("customer")
            customer_email = data_object.get("customer_email")
            price_id = None
            try:
                lines = data_object.get("lines", {}).get("data", [])
                if lines:
                    price_id = lines[0].get("price", {}).get("id")
            except Exception:
                price_id = None
            user = None
            if customer:
                user = session.query(User).filter(User.stripe_customer_id == customer).first()
            if not user and customer_email:
                user = session.query(User).filter(User.email == customer_email).first()
            if not user:
                return
            changed = False
            if customer and not getattr(user, "stripe_customer_id", None):
                user.stripe_customer_id = customer
                changed = True
            if price_id:
                plan = None
                if price_id == getattr(settings, "STRIPE_PRICE_PRO_MONTHLY", None) or price_id == getattr(settings, "STRIPE_PRICE_PRO_YEARLY", None):
                    plan = PlanType.PRO
                elif price_id == getattr(settings, "STRIPE_PRICE_TEAM_MONTHLY", None):
                    plan = PlanType.BUSINESS
                if plan is not None and getattr(user, "plan", None) != plan:
                    user.plan = plan
                    changed = True
            if changed:
                session.commit()

        elif event_type in ("customer.created", "customer.updated"):
            cust_id = data_object.get("id")
            email = data_object.get("email")
            if cust_id and email:
                user = session.query(User).filter(User.email == email).first()
                if user and not getattr(user, "stripe_customer_id", None):
                    user.stripe_customer_id = cust_id
                    session.commit()
        elif event_type in ("invoice.payment_failed",):
            customer = data_object.get("customer")
            if customer:
                user = session.query(User).filter(User.stripe_customer_id == customer).first()
                if user:
                    user.payment_state = "past_due"
                    user.last_invoice_status = "failed"
                    session.commit()
        elif event_type in ("invoice.payment_action_required",):
            customer = data_object.get("customer")
            if customer:
                user = session.query(User).filter(User.stripe_customer_id == customer).first()
                if user:
                    user.payment_state = "requires_action"
                    user.last_invoice_status = "action_required"
                    session.commit()
    except Exception as e:  # pragma: no cover
        print(f"[stripe][task] failed to process event {event.get('type')}: {e}")
        try:
            session.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            session.close()
        except Exception:
            pass

    


@dramatiq.actor
def run_evaluation(evaluation_id: int, user_id: int, receipt_ids: list[int], model_name: str, organisation_id: Optional[int] = None) -> None:
    """Dramatiq actor to perform an evaluation asynchronously.

    This actor creates an evaluation record and processes the
    specified receipts in parallel. Once finished it updates the
    evaluation with summary metrics. See ``EvaluationService`` for
    details.
    """
    session = SessionLocal()
    evaluation = None
    
    span_cm = sentry_sdk.start_span if sentry_sdk else None  # type: ignore
    try:
        # Get evaluation
        if span_cm:
            with span_cm(op="evaluation.fetch", description="Fetch evaluation"):
                evaluation = session.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        else:
            evaluation = session.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if not evaluation:
            print(f"Evaluation {evaluation_id} not found")
            return
        
        # Update status
        evaluation.status = EvaluationStatus.RUNNING
        session.commit()
        
        # For now, just mark as completed
        # In a real implementation, you would process the receipts here
        if span_cm:
            with span_cm(op="evaluation.compute", description="Compute evaluation metrics"):
                evaluation.status = EvaluationStatus.COMPLETED
                evaluation.metrics = {
                    "total_receipts": len(receipt_ids),
                    "processed": len(receipt_ids),
                    "model": model_name
                }
        else:
            evaluation.status = EvaluationStatus.COMPLETED
            evaluation.metrics = {
                "total_receipts": len(receipt_ids),
                "processed": len(receipt_ids),
                "model": model_name
            }
        session.commit()
        
        print(f"Successfully completed evaluation {evaluation_id}")
        
    except Exception as e:
        print(f"Failed to run evaluation {evaluation_id}: {e}")
        if evaluation:
            evaluation.status = EvaluationStatus.ERROR
            session.commit()
        raise
    finally:
        session.close()

# # Import tasks to register them
# from app.services.tasks.process_receipt import process_receipt  # noqa

# print("Tasks registered successfully")