"""Audit service for evaluating receipts against configured rules.

This service brings together two complementary approaches to audit
decisions:

1. **Rule engine** – A deterministic evaluator that applies user
   configured rules to the structured receipt details. It returns
   boolean flags for each rule and textual reasoning. This allows
   users to define custom checks such as thresholds, keyword
   searches, category filters or temporal restrictions.
2. **OpenAI Agents** – A language model based approach that can
   synthesise reasoning and apply nuanced logic beyond simple
   deterministic rules. For example, if users prefer the "business
   rule" mode they can prompt the agent with custom instructions and
   few‑shot examples.

This implementation prioritises the deterministic rule engine for
the core audit decision because it is transparent and cost
effective. It subsequently uses a language model to generate a
human‑readable explanation. If no rules are defined the service
falls back to a default prompt with built‑in examples similar to
the receipt_inspection notebook.
"""

from __future__ import annotations

import json
import logging
import os
from typing import List, Optional

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from agents import Agent, Runner, set_default_openai_api

from app.core.database import get_db
from app.core.config import settings
from app.models.schemas import ReceiptDetails, AuditDecision
from app.models.tables import AuditRule
from app.services.rule_engine import evaluate_rules
from app.utils.prompts import get_default_audit_prompt, get_audit_examples_string


logger = logging.getLogger(__name__)

# Use the responses API and disable sensitive data logging
set_default_openai_api("responses")
os.environ["OPENAI_AGENTS_DONT_LOG_MODEL_DATA"] = "1"


class AuditService:
    """Service responsible for auditing receipt details."""

    def __init__(self, db: AsyncSession = Depends(get_db)) -> None:
        self.db = db
        # Default model for audit reasoning
        self.model = "gpt-4o-mini"

    async def _load_active_rules(self, owner_id: int, organisation_id: Optional[int]) -> List[AuditRule]:
        """Retrieve all active rules for the user or organisation."""
        query = AuditRule.__table__.select().where(AuditRule.active.is_(True))
        if organisation_id:
            query = query.where(AuditRule.organisation_id == organisation_id)
        else:
            query = query.where(AuditRule.owner_id == owner_id)
        result = await self.db.execute(query)
        rows = result.fetchall()
        return [AuditRule(**row._mapping) for row in rows]

    async def audit(self, details: ReceiptDetails, user_id: int, organisation_id: Optional[int] = None) -> AuditDecision:
        """Evaluate a receipt using deterministic rules and optionally an LLM.

        :param details: Structured receipt details
        :param user_id: ID of the user who owns the receipt
        :param organisation_id: ID of the organisation if applicable
        :returns: ``AuditDecision`` capturing individual rule flags,
                  aggregated reasoning and whether auditing is required
        """
        # Load active rules
        rules = await self._load_active_rules(user_id, organisation_id)
        # Convert to simple dicts for the rule engine
        rule_dicts = [
            {
                "name": rule.name,
                "type": rule.type.value if hasattr(rule.type, "value") else rule.type,
                "config": rule.config,
            }
            for rule in rules
        ]
        # Evaluate deterministic rules
        flags, reasons, needs_audit = evaluate_rules(details, rule_dicts)
        # Build reasoning string
        reasoning = "\n".join(reasons)
        # Map flags onto the static audit fields. Unknown rules map to False.
        # Standard rule names expected by downstream consumers
        not_travel = flags.get("not_travel_related", False)
        over_limit = flags.get("amount_over_limit", False)
        math_error = flags.get("math_error", False)
        handwritten_x = flags.get("handwritten_x", False)
        # If there are no configured rules use the default audit agent
        if not rule_dicts:
            # Build default audit prompt with examples
            prompt = get_default_audit_prompt().format(examples=get_audit_examples_string())
            agent = Agent(
                name="receipt_audit_agent_default",
                instructions=prompt,
                model=self.model,
                output_type=AuditDecision,
            )
            # Use the receipt details as JSON input
            input_message = f"Audit this receipt data:\n\n{details.model_dump_json(indent=2)}"
            try:
                result = await Runner.run(agent, input_message)
                decision: AuditDecision = result.final_output
                return decision
            except Exception as exc:
                logger.error(f"Audit agent failed: {exc}")
                return AuditDecision(
                    not_travel_related=False,
                    amount_over_limit=False,
                    math_error=False,
                    handwritten_x=False,
                    reasoning=f"Audit agent error: {exc}",
                    needs_audit=True,
                )
        # Otherwise combine deterministic flags into the decision object
        decision = AuditDecision(
            not_travel_related=not_travel,
            amount_over_limit=over_limit,
            math_error=math_error,
            handwritten_x=handwritten_x,
            reasoning=reasoning,
            needs_audit=needs_audit,
        )
        return decision