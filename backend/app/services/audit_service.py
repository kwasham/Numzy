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
import httpx

from app.core.database import get_db
from app.core.config import settings
from app.models.schemas import ReceiptDetails, AuditDecision
from app.models.tables import AuditRule
from app.services.rule_engine import evaluate_rules
from app.utils.prompts import get_default_audit_prompt, get_audit_examples_string
from app.models.enums import RuleType
from app.services.prompt_templates import prompt_template_repository


logger = logging.getLogger(__name__)

# If the OpenAI Agents SDK is available, configure it. Otherwise, continue.
try:  # optional dependency
    from agents import set_default_openai_api  # type: ignore
    # Use the responses API and disable sensitive data logging
    set_default_openai_api("responses")
    os.environ["OPENAI_AGENTS_DONT_LOG_MODEL_DATA"] = "1"
except Exception:  # pragma: no cover - non-fatal
    pass


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
    
    
    async def _get_audit_instructions(self, rule_description: str, amount_limit: float) -> str:
        """Fetch audit instructions via MCP if available, else synthesize a default string.

        This avoids a hard dependency on the optional `agents` SDK by falling back
        to a deterministic template when the SDK isn't installed.
        """
        mcp_url = os.getenv("MCP_URL", "http://mcp_server:8000")
        try:
            # Try to import the Agents MCP HTTP client only when needed
            from agents.mcp import MCPServerStreamableHttp  # type: ignore

            async with MCPServerStreamableHttp(
                name="receipt-audit-mcp",
                params={"url": f"{mcp_url}/mcp"},
            ) as mcp_client:
                prompt_result = await mcp_client.get_prompt(
                    "generate_audit_instructions",
                    {
                        "rule_description": rule_description,
                        "amount_limit": str(amount_limit),
                    },
                )
                return prompt_result.messages[0].content.text
        except Exception:  # If MCP isn't available, return a basic instruction string
            return (
                "Evaluate the receipt against the following constraints: "
                f"{rule_description}. Flag if amount exceeds {amount_limit:.2f}."
            )

    async def audit(
        self,
        details: ReceiptDetails,
        user_id: int,
        organisation_id: Optional[int] = None,
        
    ) -> AuditDecision:
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
        # First, evaluate deterministic rules as before...
        flags, reasons, needs_audit = evaluate_rules(details, rule_dicts)
        reasoning = "\n".join(reasons)
        
        # Check for any LLM-based rules
        for rule in rules:
            if rule.type == RuleType.LLM:
                prompt_id = rule.config.get("prompt_id")
                threshold = float(rule.config.get("threshold", 50.0))
                # Retrieve the prompt template from the DB
                prompt_record = await prompt_template_repository.get(prompt_id)
                instructions = prompt_record.content
                try:
                    # Import the optional Agents SDK only where needed
                    from agents import Agent, Runner  # type: ignore
                    from agents.model_settings import ModelSettings  # type: ignore

                    agent = Agent(
                        name="dynamic_audit_agent",
                        instructions=instructions,
                        model_settings=ModelSettings(tool_choice="auto"),
                        output_type=AuditDecision,
                    )
                    input_message = (
                        f"Audit this receipt:\n{details.model_dump_json(indent=2)}"
                    )
                    result = await Runner.run(starting_agent=agent, input=input_message)
                    return result.final_output
                except Exception as exc:
                    logger.warning(
                        "LLM rule configured but Agents SDK not available or failed (%s); "
                        "falling back to deterministic rules.",
                        exc,
                    )
                    # Continue to deterministic result below

        # ...if no LLM rules, return deterministic result
        return AuditDecision(
            not_travel_related=flags.get("not_travel_related", False),
            amount_over_limit=flags.get("amount_over_limit", False),
            math_error=flags.get("math_error", False),
            handwritten_x=flags.get("handwritten_x", False),
            reasoning=reasoning,
            needs_audit=needs_audit,
        )