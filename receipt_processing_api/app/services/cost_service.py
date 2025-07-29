"""Cost analysis service.

This service computes the financial impact of audit performance
metrics. It uses the false positive and false negative rates from
an evaluation to estimate how many receipts will be audited
unnecessarily and how many problematic receipts will be missed.
Coupled with per‑receipt processing cost, audit cost and penalty
cost for missed audits it outputs an annualised cost summary.
"""

from __future__ import annotations

from typing import Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.tables import Evaluation, EvaluationItem


class CostService:
    """Service for performing cost analyses on evaluation results."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyse(
        self,
        evaluation_id: int,
        false_positive_rate: float,
        false_negative_rate: float,
        per_receipt_cost: float,
        audit_cost_per_receipt: float,
        missed_audit_penalty: float,
    ) -> Dict[str, Any]:
        """Perform cost analysis based on user supplied rates and costs.

        :param evaluation_id: ID of the evaluation record
        :param false_positive_rate: Fraction of receipts incorrectly flagged as needing audit
        :param false_negative_rate: Fraction of receipts incorrectly allowed through
        :param per_receipt_cost: Baseline cost to process each receipt (model inference, storage, etc.)
        :param audit_cost_per_receipt: Cost of a human auditor reviewing a flagged receipt
        :param missed_audit_penalty: Penalty cost for a missed fraudulent or non‑compliant receipt
        :returns: Dictionary containing cost breakdown and total
        """
        # Count total receipts processed in the evaluation
        eval_row = await self.db.get(Evaluation, evaluation_id)
        if not eval_row or not eval_row.items:
            return {
                "error": "Evaluation not found or has no items"
            }
        total_receipts = len(eval_row.items)
        # Compute expected counts using provided rates
        false_positives = false_positive_rate * total_receipts
        false_negatives = false_negative_rate * total_receipts
        audits = false_positives  # receipts unnecessarily audited
        missed = false_negatives  # receipts that should have been audited
        audit_cost = audits * audit_cost_per_receipt
        missed_cost = missed * missed_audit_penalty
        processing_cost = total_receipts * per_receipt_cost
        total_cost = audit_cost + missed_cost + processing_cost
        return {
            "total_receipts": total_receipts,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "audit_cost": audit_cost,
            "missed_cost": missed_cost,
            "processing_cost": processing_cost,
            "total_cost": total_cost,
        }