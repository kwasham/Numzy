"""Evaluation service for benchmarking extraction and audit models.

The evaluation service orchestrates the process of running the
extraction and audit services on a set of receipts and computing
simple accuracy metrics. It stores the results in the database and
returns summary statistics to the caller. This component is
inspired by the OpenAI Evals integration but runs the evaluation
locally to avoid external dependencies. You can extend this
implementation to call the OpenAI Evals API if you wish to use
their graders and dashboards.
"""

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Dict, List, Optional

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.enums import EvaluationStatus
from app.models.schemas import ReceiptDetails, AuditDecision
from app.models.tables import Receipt, Evaluation, EvaluationItem
from app.services.extraction_service import ExtractionService
from app.services.audit_service import AuditService


class EvaluationService:
    """Service that runs evaluations across multiple receipts."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        self.extraction_service = ExtractionService()
        # AuditService needs a db dependency; we'll provide via injection later
        # When creating tasks we'll pass the db session explicitly

    async def _evaluate_receipt(
        self,
        receipt: Receipt,
        model_name: str,
        user_id: int,
        organisation_id: Optional[int],
    ) -> Dict[str, any]:
        """Process a single receipt and compute prediction/ground truth pairs."""
        # Load image data
        path = receipt.file_path
        full_path = receipt.file_path
        # On evaluation we trust that the extracted_data and audit_decision
        # stored on the receipt represent ground truth. In a real system
        # ground truth would be stored separately.
        correct_details = None
        correct_audit = None
        if receipt.extracted_data:
            correct_details = ReceiptDetails.model_validate(receipt.extracted_data)
        if receipt.audit_decision:
            correct_audit = AuditDecision.model_validate(receipt.audit_decision)
        # Load file data from storage
        from app.services.storage_service import StorageService
        storage = StorageService()
        file_bytes = storage.get_full_path(path).read_bytes()
        # Run extraction
        predicted_details = await self.extraction_service.extract(file_bytes, receipt.filename, model=model_name)
        # Run audit
        # Create a new AuditService per evaluation to ensure fresh db binding
        audit_service = AuditService(self.db)
        predicted_audit = await audit_service.audit(predicted_details, user_id, organisation_id)
        return {
            "correct_details": correct_details,
            "predicted_details": predicted_details,
            "correct_audit": correct_audit,
            "predicted_audit": predicted_audit,
        }

    def _compute_metrics(
        self,
        items: List[EvaluationItem],
    ) -> Dict[str, float]:
        """Compute simple accuracy metrics from evaluation items."""
        if not items:
            return {
                "details_accuracy": 0.0,
                "audit_accuracy": 0.0,
            }
        detail_correct = 0
        audit_correct = 0
        total = len(items)
        for item in items:
            cd = item.correct_receipt_details
            pd = item.predicted_receipt_details
            ca = item.correct_audit_decision
            pa = item.predicted_audit_decision
            # Check detail equality on merchant, total and item count
            if cd and pd and cd.get("merchant") == pd.get("merchant") and cd.get("total") == pd.get("total") and len(cd.get("items", [])) == len(pd.get("items", [])):
                detail_correct += 1
            if ca and pa and ca.get("needs_audit") == pa.get("needs_audit"):
                audit_correct += 1
        return {
            "details_accuracy": detail_correct / total,
            "audit_accuracy": audit_correct / total,
        }

    async def create_evaluation(self, user_id: int, receipt_ids: List[int], model_name: str, organisation_id: Optional[int] = None) -> Evaluation:
        """Run an evaluation on a set of receipts and persist results."""
        # Verify receipts belong to user or organisation
        query = Receipt.__table__.select().where(Receipt.id.in_(receipt_ids))
        result = await self.db.execute(query)
        rows = result.fetchall()
        if not rows:
            raise HTTPException(status_code=404, detail="No receipts found")
        receipts = [Receipt(**row._mapping) for row in rows]
        # Create evaluation record
        evaluation = Evaluation(
            owner_id=user_id,
            organisation_id=organisation_id,
            model_name=model_name,
            status=EvaluationStatus.CREATED,
        )
        self.db.add(evaluation)
        await self.db.commit()
        await self.db.refresh(evaluation)
        # Process receipts concurrently
        tasks = [
            self._evaluate_receipt(r, model_name, user_id, organisation_id)
            for r in receipts
        ]
        results = await asyncio.gather(*tasks)
        # Create evaluation items
        items: List[EvaluationItem] = []
        for r, res in zip(receipts, results):
            correct_details = res["correct_details"].model_dump() if res["correct_details"] else None
            predicted_details = res["predicted_details"].model_dump()
            correct_audit = res["correct_audit"].model_dump() if res["correct_audit"] else None
            predicted_audit = res["predicted_audit"].model_dump()
            item = EvaluationItem(
                evaluation_id=evaluation.id,
                receipt_id=r.id,
                predicted_receipt_details=predicted_details,
                predicted_audit_decision=predicted_audit,
                correct_receipt_details=correct_details,
                correct_audit_decision=correct_audit,
            )
            items.append(item)
        self.db.add_all(items)
        # Compute metrics
        summary = self._compute_metrics(items)
        evaluation.summary_metrics = summary
        evaluation.status = EvaluationStatus.COMPLETED
        await self.db.commit()
        await self.db.refresh(evaluation)
        return evaluation