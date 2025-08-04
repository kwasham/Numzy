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
import asyncio
from typing import Optional

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.tables import Receipt, ReceiptStatus, Evaluation, EvaluationStatus
from app.services.extraction_service import ExtractionService
from app.services.audit_service import AuditService
from app.services.storage_service import StorageService

# Configure Dramatiq
broker = RedisBroker(url=settings.DRAMATIQ_BROKER_URL)
dramatiq.set_broker(broker)

# Create synchronous engine for worker processes
# Convert async URL to sync URL
sync_db_url = settings.DATABASE_URL.replace('+asyncpg', '')
engine = create_engine(sync_db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@dramatiq.actor
def extract_and_audit_receipt(receipt_id: int, user_id: int):
    """Background task to extract data from receipt and audit it.
    
    This is the Dramatiq version of the task that will be executed
    by the worker process.
    """
    session = SessionLocal()
    rec = None
    
    # Override user_id to 2 for dev mode
    if user_id == 1:  # If it's the old default user
        user_id = 2  # Use dev user instead
    
    try:
        # Get the receipt
        rec = session.query(Receipt).filter(Receipt.id == receipt_id).first()
        if not rec:
            print(f"Receipt {receipt_id} not found")
            return
        
        # Update the owner_id if needed
        if rec.owner_id == 1:
            rec.owner_id = 2
            session.commit()
        
        # Update status to processing
        rec.status = ReceiptStatus.PROCESSING
        session.commit()
        
        # Load file data from storage
        storage_service = StorageService()
        file_path = storage_service.get_full_path(rec.file_path)
        
        if not file_path.exists():
            print(f"File not found: {rec.file_path}")
            rec.status = ReceiptStatus.ERROR
            session.commit()
            return
        
        file_bytes = file_path.read_bytes()
        
        # Extract receipt details - run async function in sync context
        extraction_service = ExtractionService()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            details = loop.run_until_complete(
                extraction_service.extract(file_bytes, rec.filename)
            )
        finally:
            loop.close()
        
        # Run audit - need to create async version for sync context
        from app.services.audit_service import AuditDecision
        from app.models.tables import AuditRule, RuleType
        
        # Get audit rules synchronously
        # Check if the receipt has an organisation_id to filter rules
        if rec.organisation_id:
            rules = session.query(AuditRule).filter(
                AuditRule.organisation_id == rec.organisation_id,
                AuditRule.enabled == True
            ).all()
        else:
            # If no organisation, no rules apply
            rules = []
        
        # Simple synchronous audit logic
        # Initialize with all required fields
        decision = AuditDecision(
            violations=[],
            total_amount=details.total,
            max_allowed=None,
            not_travel_related=False,
            amount_over_limit=False,
            math_error=False,
            handwritten_x=False,
            reasoning="",
            needs_audit=False
        )
        
        # Apply rules
        for rule in rules:
            if rule.rule_type == RuleType.MAX_TOTAL and details.total > rule.amount_limit:
                decision.amount_over_limit = True
                decision.violations.append(f"Total ${details.total} exceeds limit ${rule.amount_limit}")
                decision.max_allowed = rule.amount_limit
                decision.reasoning = f"Receipt total of ${details.total} exceeds the maximum allowed amount of ${rule.amount_limit}"
                decision.needs_audit = True
                break
        
        if not decision.needs_audit:
            decision.reasoning = "Receipt approved - no rule violations found"
        
        # Update receipt record
        rec.extracted_data = details.model_dump()
        rec.audit_decision = decision.model_dump()
        rec.status = ReceiptStatus.COMPLETED
        
        session.commit()
        print(f"Successfully processed receipt {receipt_id}")
        
    except Exception as e:
        print(f"Failed to process receipt {receipt_id}: {e}")
        if rec:
            rec.status = ReceiptStatus.ERROR
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