"""Dynamic rule engine for evaluating receipts.

The rule engine interprets a series of user-defined rules and applies
them to a ``ReceiptDetails`` object, producing a dictionary of
boolean flags and a textual reasoning for each rule. Rules are
represented by the ``AuditRule`` model in the database. Each rule
has a ``type`` (see :mod:`app.models.enums.RuleType`) and a
configuration object stored as JSON. This engine converts those
configurations into concrete checks.

Supported rule types:

* ``threshold`` – Compare a numeric field of the receipt (such as
  ``total`` or ``subtotal``) against a constant. Operators include
  ``>``, ``>=``, ``<``, ``<=`` and ``==``.
* ``keyword`` – Check if any of the specified keywords appear in
  the line item descriptions or categories.
* ``category`` – Flag receipts containing line items within a set
  of categories (e.g. ``alcohol``, ``travel``, ``office supplies``).
* ``time`` – Detect receipts that occur outside business hours,
  within specified date ranges or during weekends.

Other rule types (``pattern``, ``ml``, ``python``, ``llm``) are
placeholder stubs that always return ``False``. Extend these
handlers to support advanced functionality such as anomaly
detectors, arbitrary user‑supplied expressions or LLM based
evaluation.

The engine returns a tuple of a dictionary mapping rule names to
boolean flags indicating whether the rule was triggered, and a
list of reasoning strings that can be concatenated for the final
audit decision. A receipt requires auditing if any rule flag is
``True``.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional, Tuple

from app.models.enums import RuleType
from app.models.schemas import ReceiptDetails, LineItem


def _parse_amount(value: str | None) -> float:
    """Safely parse a monetary amount from a string.

    Returns 0.0 if the value is missing or cannot be parsed. Removes
    currency symbols and commas before conversion.
    """
    if not value:
        return 0.0
    try:
        cleaned = value.replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except Exception:
        return 0.0


def _get_field_value(details: ReceiptDetails, field: Optional[str]) -> Any:
    """Extract a field value from receipt details."""
    if field is None:
        return 0.0  # Return 0 for None field instead of None

    if field.startswith("items."):
        _, subfield = field.split(".", 1)
        total = 0.0
        for item in details.items:
            val = getattr(item, subfield, None)
            total += _parse_amount(val)
        return total
    # Direct attribute
    val = getattr(details, field, None)
    return _parse_amount(val)


def _evaluate_threshold(details: ReceiptDetails, config: Dict[str, Any]) -> Tuple[bool, str]:
    """Evaluate a threshold rule."""
    field = config.get("field")
    op = config.get("op")
    value = config.get("value", 0)
    
    # Handle missing field
    if field is None:
        return False, "missing field in threshold rule config"
    
    amount = _get_field_value(details, field)
    if op == ">":
        triggered = amount > value
    elif op == ">=":
        triggered = amount >= value
    elif op == "<":
        triggered = amount < value
    elif op == "<=":
        triggered = amount <= value
    elif op == "==":
        triggered = amount == value
    else:
        triggered = False
    reasoning = f"{field} ({amount:.2f}) {op} {value} -> {triggered}"
    return triggered, reasoning


def _evaluate_keyword(details: ReceiptDetails, config: Dict[str, Any]) -> Tuple[bool, str]:
    """Evaluate a keyword rule.

    The config should include a ``keywords`` list. The rule is
    triggered if any keyword appears in a line item's description
    or category (case insensitive). Example:

    ```json
    {"keywords": ["alcohol", "beer"]}
    ```
    """
    keywords = [kw.lower() for kw in config.get("keywords", [])]
    triggered = False
    matched_keywords: List[str] = []
    for item in details.items:
        desc = (item.description or "").lower()
        cat = (item.category or "").lower()
        for kw in keywords:
            if kw in desc or kw in cat:
                triggered = True
                matched_keywords.append(kw)
    reasoning = (
        f"keywords {keywords} matched {matched_keywords} -> {triggered}"
    )
    return triggered, reasoning


def _evaluate_category(details: ReceiptDetails, config: Dict[str, Any]) -> Tuple[bool, str]:
    """Evaluate a category rule.

    The config should include a ``categories`` list. The rule is
    triggered if any line item category matches one of the configured
    categories (case insensitive). Example:

    ```json
    {"categories": ["alcohol", "travel"]}
    ```
    """
    categories = [c.lower() for c in config.get("categories", [])]
    triggered = False
    matched: List[str] = []
    for item in details.items:
        cat = (item.category or "").lower()
        if cat in categories:
            triggered = True
            matched.append(cat)
    reasoning = f"categories {categories} matched {matched} -> {triggered}"
    return triggered, reasoning


def _evaluate_time(details: ReceiptDetails, config: Dict[str, Any]) -> Tuple[bool, str]:
    """Evaluate a time rule.

    Supported configurations:

    * ``after_hours``: If true, flags receipts outside 09:00–17:00.
    * ``weekend``: If true, flags receipts on Saturday or Sunday.
    * ``date_range``: A list of two ISO dates; flags receipts
      falling outside of the range.
    """
    timestamp = details.time
    if not timestamp:
        return False, "no timestamp available"
    try:
        dt_obj = dt.datetime.fromisoformat(timestamp)
    except Exception:
        return False, f"invalid timestamp {timestamp}"
    triggered = False
    messages: List[str] = []
    if config.get("after_hours"):
        if dt_obj.hour < 9 or dt_obj.hour >= 17:
            triggered = True
            messages.append("after hours")
    if config.get("weekend"):
        if dt_obj.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
            triggered = True
            messages.append("weekend")
    if "date_range" in config:
        start, end = config["date_range"]
        start_date = dt.date.fromisoformat(start)
        end_date = dt.date.fromisoformat(end)
        if not (start_date <= dt_obj.date() <= end_date):
            triggered = True
            messages.append(f"outside {start}–{end}")
    reasoning = ", ".join(messages) if messages else "within allowed times"
    return triggered, reasoning


def _evaluate_stub(details: ReceiptDetails, config: Dict[str, Any]) -> Tuple[bool, str]:
    """Placeholder evaluator for unimplemented rule types."""
    return False, "unsupported rule type"


HANDLERS = {
    RuleType.THRESHOLD: _evaluate_threshold,
    RuleType.KEYWORD: _evaluate_keyword,
    RuleType.CATEGORY: _evaluate_category,
    RuleType.TIME: _evaluate_time,
    RuleType.PATTERN: _evaluate_stub,
    RuleType.ML: _evaluate_stub,
    RuleType.PYTHON: _evaluate_stub,
    RuleType.LLM: _evaluate_stub,
}


def evaluate_rules(
    details: ReceiptDetails,
    rules: List[Dict[str, Any]],
) -> Tuple[Dict[str, bool], List[str], bool]:
    """Evaluate multiple rules against a receipt.

    :param details: Structured receipt details.
    :param rules: A list of rule dictionaries each containing
        ``name``, ``type`` and ``config`` keys. This structure mirrors
        what is stored in the AuditRule model but avoids coupling
        directly to SQLAlchemy objects which simplifies usage in
        services.
    :returns: A tuple of (flags, reasons, needs_audit) where ``flags``
        maps the rule name to a boolean value indicating whether the
        rule fired, ``reasons`` is a list of reasoning strings, and
        ``needs_audit`` is ``True`` if any rule fired.
    """
    flags: Dict[str, bool] = {}
    reasons: List[str] = []
    overall = False
    for rule in rules:
        rule_name = rule.get("name")
        rule_type = rule.get("type")
        config = rule.get("config", {})
        handler = HANDLERS.get(RuleType(rule_type), _evaluate_stub)
        triggered, reason = handler(details, config)
        flags[rule_name] = triggered
        reasons.append(f"{rule_name}: {reason}")
        if triggered:
            overall = True
    return flags, reasons, overall