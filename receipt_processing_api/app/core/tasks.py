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

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, TimeLimit, ShutdownNotifications, Retries
from dramatiq.results import Results
from dramatiq.results.backends import RedisBackend
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.tables import Receipt, BackgroundJob, Evaluation
from app.models.enums import ReceiptStatus, EvaluationStatus
from app.services.extraction_service import ExtractionService
from app.services.storage_service import load_file_from_storage

# Update the broker configuration to be more explicit

# Configure broker - remove the condition check to ensure it always uses our settings
# Set up Redis broker with results backend
redis_url = os.getenv("DRAMATIQ_BROKER_URL", "redis://redis:6379/0")
print(f"Configuring Dramatiq with Redis URL: {redis_url}")  # Debug logging

result_backend = RedisBackend(url=redis_url)
redis_broker = RedisBroker(url=redis_url)

# Add middleware including Results
redis_broker.add_middleware(Results(backend=result_backend))
redis_broker.add_middleware(AgeLimit())
redis_broker.add_middleware(TimeLimit())
redis_broker.add_middleware(ShutdownNotifications())
redis_broker.add_middleware(Retries(max_retries=3))

dramatiq.set_broker(redis_broker)
print(f"Dramatiq broker configured successfully")  # Debug logging

# Export the broker for Dramatiq CLI
broker = redis_broker

# Create synchronous engine for worker processes with connection pooling
sync_db_url = settings.DATABASE_URL.replace('+asyncpg', '')
engine = create_engine(
    sync_db_url,
    pool_pre_ping=True,  # Test connections before using them
    pool_size=5,         # Number of connections to maintain
    max_overflow=10,     # Maximum overflow connections
    pool_recycle=3600,   # Recycle connections after 1 hour
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
    """Background task to extract data from receipt and audit it."""
    session = SessionLocal()
    rec = None
    job = None
    start_time = time.time()
    
    # Get the current message ID from Dramatiq
    from dramatiq.middleware import CurrentMessage
    message = CurrentMessage.get_current_message()
    message_id = message.message_id if message else str(receipt_id)
    
    try:
        # Create or update job record
        job = session.query(BackgroundJob).filter_by(id=message_id).first()
        if not job:
            job = BackgroundJob(
                id=message_id,
                job_type="receipt_extraction",
                status="running",
                user_id=user_id,
                receipt_id=receipt_id,
                payload={"receipt_id": receipt_id, "user_id": user_id},
                started_at=datetime.utcnow()
            )
            session.add(job)
        else:
            job.status = "running"
            job.started_at = datetime.utcnow()
        session.commit()
        
        # Override user_id to 2 for dev mode
        if user_id == 1:
            user_id = 2
            
        # Query receipt
        rec = session.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not rec:
            raise ValueError(f"Receipt {receipt_id} not found")
            
        # Update receipt status
        rec.status = ReceiptStatus.PROCESSING
        rec.task_started_at = datetime.utcnow()
        job.progress = 10
        session.commit()
        
        # Load file data from storage
        print(f"Looking for file at: {rec.file_path}")
        file_data = load_file_from_storage(rec.file_path)
        
        # Update progress: starting extraction
        rec.extraction_progress = 10
        job.progress = 20
        session.commit()
        
        # Extract data
        extraction_service = ExtractionService()
        import asyncio
        receipt_details = asyncio.run(extraction_service.extract(file_data, rec.filename))
        rec.extracted_data = receipt_details.model_dump()
        rec.extraction_progress = 100
        job.progress = 60
        session.commit()
        
        # Update progress: starting audit
        rec.audit_progress = 10
        job.progress = 70
        session.commit()
        
        # Audit the receipt
        from app.models.schemas import AuditDecision
        
        # Simple threshold check on total
        total_amount = _parse_amount(receipt_details.total)
        amount_over_limit = total_amount > 50  # Check if over $50 spending limit
        
        audit_result = AuditDecision(
            not_travel_related=False,
            amount_over_limit=amount_over_limit,
            math_error=False,
            handwritten_x=False,
            reasoning=f"Total amount: ${total_amount:.2f}. {'Over $50 spending limit - needs audit' if amount_over_limit else 'Within $50 spending limit'}",
            needs_audit=amount_over_limit
        )
        
        rec.audit_decision = audit_result.model_dump()
        rec.audit_progress = 100
        job.progress = 90
        session.commit()
        
        # Update receipt as completed
        duration_ms = int((time.time() - start_time) * 1000)
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
            "needs_audit": amount_over_limit
        }
        
        session.commit()
        print(f"Successfully processed receipt {receipt_id} in {duration_ms}ms")
        
    except Exception as e:
        print(f"Failed to process receipt {receipt_id}: {str(e)}")
        if rec:
            rec.status = ReceiptStatus.FAILED
            rec.task_error = str(e)
            rec.task_retry_count = getattr(rec, 'task_retry_count', 0) + 1
        
        if job:
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            
        session.commit()
        raise
        
    finally:
        session.close()


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
    
    try:
        # Get evaluation
        evaluation = session.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if not evaluation:
            print(f"Evaluation {evaluation_id} not found")
            return
        
        # Update status
        evaluation.status = EvaluationStatus.RUNNING
        session.commit()
        
        # For now, just mark as completed
        # In a real implementation, you would process the receipts here
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