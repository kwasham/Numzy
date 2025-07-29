"""Celery task definitions for background processing.

In production the receipt processing pipeline may involve long
running operations such as running vision models, auditing with
language models and persisting results. Celery provides a robust
framework for executing these tasks asynchronously via a message
broker like Redis or RabbitMQ. This module defines Celery tasks
that mirror the functionality used in FastAPI background tasks.

To run these tasks you must start a Celery worker pointed at the
module:

```bash
celery -A receipt_processing_api.app.core.tasks worker --loglevel=info
```

The broker URL defaults to Redis at ``redis://localhost:6379/0``. You
can override it via the ``CELERY_BROKER_URL`` environment variable.
"""

from __future__ import annotations

import os
import asyncio
from typing import Optional

from celery import Celery

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.tables import Receipt, ReceiptStatus
from app.services.extraction_service import ExtractionService
from app.services.audit_service import AuditService


# Configure Celery
broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
app = Celery("tasks", broker=broker_url)


@app.task
def extract_and_audit_receipt(receipt_id: int, user_id: int, organisation_id: Optional[int] = None) -> None:
    """Celery task to run extraction and audit on a receipt.

    This task loads the receipt from the database, performs the
    extraction and audit using the services and updates the
    receipt record. It runs inside a synchronous Celery worker but
    uses an event loop internally to call async services.
    """
    async def _run() -> None:
        async with async_session_factory() as session:
            rec = await session.get(Receipt, receipt_id)
            if not rec:
                return
            rec.status = ReceiptStatus.PROCESSING
            await session.commit()
            # Load file data from storage
            from app.services.storage_service import StorageService
            storage = StorageService()
            file_bytes = storage.get_full_path(rec.file_path).read_bytes()
            extraction_service = ExtractionService()
            details = await extraction_service.extract(file_bytes, rec.filename)
            audit_service = AuditService(session)
            decision = await audit_service.audit(details, user_id, organisation_id)
            rec.extracted_data = details.model_dump()
            rec.audit_decision = decision.model_dump()
            rec.status = ReceiptStatus.COMPLETED
            await session.commit()
    asyncio.run(_run())


@app.task
def run_evaluation(evaluation_id: int, user_id: int, receipt_ids: list[int], model_name: str, organisation_id: Optional[int] = None) -> None:
    """Celery task to perform an evaluation asynchronously.

    This task creates an evaluation record and processes the
    specified receipts in parallel. Once finished it updates the
    evaluation with summary metrics. See ``EvaluationService`` for
    details.
    """
    async def _run() -> None:
        async with async_session_factory() as session:
            from app.services.evaluation_service import EvaluationService
            service = EvaluationService(session)
            await service.create_evaluation(user_id, receipt_ids, model_name, organisation_id)
    asyncio.run(_run())