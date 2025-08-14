"""Enumeration types used throughout the receipt processing API.

Enumerations make it easier to constrain the values that can be
stored in the database or passed through the API. They also
improve readability when dealing with domain concepts like plan
levels, rule types or processing statuses.

When modifying these enums you should update any corresponding
database columns or Pydantic validators so that new values are
accepted where appropriate.
"""

from enum import Enum


class PlanType(str, Enum):
    """Subscription tier for a user or organisation."""

    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class RuleType(str, Enum):
    """Categories of audit rules supported by the rule engine."""

    THRESHOLD = "threshold"
    KEYWORD = "keyword"
    CATEGORY = "category"
    TIME = "time"
    PATTERN = "pattern"
    ML = "ml"
    PYTHON = "python"
    LLM = "llm"


class ReceiptStatus(str, Enum):
    """Processing states for a receipt."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EvaluationStatus(str, Enum):
    """Status of an evaluation run."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"