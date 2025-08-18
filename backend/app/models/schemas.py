"""Pydantic schemas for request and response models.

Pydantic models are used for validating and serialising data that
crosses the boundary of the API. They provide type hints and
validation rules that ensure only well‑formed data enters the
business logic. This module defines both the domain schemas (e.g.
``ReceiptDetails``, ``AuditDecision``) and API facing schemas for
creating, updating and returning resources such as receipts,
audit rules and evaluations.

Whenever you modify the underlying SQLAlchemy models be sure to
update these Pydantic models accordingly. Note that Pydantic
schemas are intentionally separate from the ORM models to avoid
coupling and to allow for different shapes of data being exposed
through the API compared with what is stored in the database.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ConfigDict

from .enums import PlanType, RuleType, ReceiptStatus, EvaluationStatus


# ---------------------------------------------------------------------------
# Domain schemas used by OpenAI Agents for structured output


class Location(BaseModel):
    """Location information from a receipt."""

    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None


class LineItem(BaseModel):
    """Individual line item on a receipt."""

    description: Optional[str] = None
    product_code: Optional[str] = None
    category: Optional[str] = None
    item_price: Optional[str] = None
    sale_price: Optional[str] = None
    quantity: Optional[str] = None
    total: Optional[str] = None


class PaymentMethod(BaseModel):
    """Payment method details parsed from the receipt."""

    type: Optional[str] = Field(default=None, description="Type of payment method, e.g., card, cash")
    brand: Optional[str] = Field(default=None, description="Brand for card payments, e.g., Visa, Mastercard")
    last4: Optional[str] = Field(default=None, description="Last 4 digits for card payments if visible")
    cardholder: Optional[str] = Field(default=None, description="Name on card if present")


class ReceiptDetails(BaseModel):
    """Complete structured receipt details used as the output of extraction."""

    merchant: Optional[str] = None
    location: Location = Field(default_factory=Location)
    time: Optional[str] = None
    items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[str] = None
    tax: Optional[str] = None
    total: Optional[str] = None
    handwritten_notes: List[str] = Field(default_factory=list)
    payment_method: PaymentMethod = Field(default_factory=PaymentMethod)


class AuditDecision(BaseModel):
    """Structured audit decision returned by the audit service."""

    not_travel_related: bool = Field(description="True if the receipt is not travel‑related")
    amount_over_limit: bool = Field(description="True if the total amount exceeds a configured limit")
    math_error: bool = Field(description="True if there are math errors in the receipt totals")
    handwritten_x: bool = Field(description="True if there is an 'X' in the handwritten notes")
    reasoning: str = Field(description="Explanation for the audit decision")
    needs_audit: bool = Field(description="Final determination if receipt needs auditing")


class ProcessingResult(BaseModel):
    """Result of processing a single receipt including extraction and audit."""

    receipt_details: ReceiptDetails
    audit_decision: AuditDecision
    processing_time_ms: float
    costs: Dict[str, Any]
    processing_successful: bool = True
    error_message: Optional[str] = None


class EvaluationRecord(BaseModel):
    """Record used for evaluating predictions against ground truth."""

    receipt_image_path: str
    correct_receipt_details: ReceiptDetails
    predicted_receipt_details: ReceiptDetails
    correct_audit_decision: AuditDecision
    predicted_audit_decision: AuditDecision


# ---------------------------------------------------------------------------
# API request/response schemas

class UserRead(BaseModel):
    id: int
    clerk_id: str
    email: str
    stripe_customer_id: Optional[str] = None
    name: str
    plan: PlanType
    created_at: datetime
    updated_at: datetime


# Schema for creating a new user
class UserCreate(BaseModel):
    clerk_id: str
    email: str
    name: str
    plan: PlanType = PlanType.FREE

    @field_validator("name", "email", "clerk_id", mode="before")
    def sanitize_fields(cls, v):
        from app.utils.sanitization import sanitize_string
        return sanitize_string(v) if v is not None else v

# Schema for updating an existing user
class UserUpdate(BaseModel):
    name: Optional[str] = None
    plan: Optional[PlanType] = None
    stripe_customer_id: Optional[str] = None

    @field_validator("name", mode="before")
    def sanitize_name(cls, v):
        from app.utils.sanitization import sanitize_string
        return sanitize_string(v) if v is not None else v


class ReceiptRead(BaseModel):
    id: int
    filename: str
    status: ReceiptStatus
    extracted_data: Optional[Dict[str, Any]] = None
    audit_decision: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    task_id: Optional[str] = None
    processing_duration_ms: Optional[int] = None
    job_id: Optional[str] = None  # Add this field
    extraction_progress: int = 0
    audit_progress: int = 0

    model_config = ConfigDict(from_attributes=True)


class ReceiptListResponse(BaseModel):
    receipts: List[ReceiptRead]


class AuditRuleBase(BaseModel):
    name: str
    type: RuleType
    config: Dict[str, Any]
    active: bool = True


class AuditRuleCreate(AuditRuleBase):
    pass

class AuditRuleNLCreate(BaseModel):
    """
    Schema for creating an LLM-based audit rule from a natural-language description.
    """
    name: str               # e.g. "High Weekend Receipts"
    description: str        # Natural-language rule text
    threshold: float = 50.0 # Optional amount limit or other parameter


class AuditRuleUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None


class AuditRuleRead(AuditRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptTemplateBase(BaseModel):
    name: str
    type: str
    content: str


class PromptTemplateCreate(PromptTemplateBase):
    @field_validator("name", "type", "content", mode="before")
    def sanitize_fields(cls, v):
        from app.utils.sanitization import sanitize_string
        return sanitize_string(v) if v is not None else v


class PromptTemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None

    @field_validator("name", "content", mode="before")
    def sanitize_fields(cls, v):
        from app.utils.sanitization import sanitize_string
        return sanitize_string(v) if v is not None else v


class PromptTemplateRead(PromptTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvaluationCreate(BaseModel):
    model_name: str = Field(description="Name of the LLM model to use for predictions")
    receipt_ids: List[int] = Field(description="List of receipt IDs to include in the evaluation")


class EvaluationSummary(BaseModel):
    id: int
    model_name: str
    status: EvaluationStatus
    summary_metrics: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CostAnalysisCreate(BaseModel):
    evaluation_id: int
    false_positive_rate: float
    false_negative_rate: float
    per_receipt_cost: float
    audit_cost_per_receipt: float
    missed_audit_penalty: float


class CostAnalysisRead(BaseModel):
    id: int
    evaluation_id: int
    parameters: Dict[str, Any]
    result: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Api for updating receipts
class ReceiptUpdate(BaseModel):
    filename: Optional[str] = None
    status: Optional[ReceiptStatus] = None
    extracted_data: Optional[Dict[str, Any]] = None
    audit_decision: Optional[Dict[str, Any]] = None
    updated_at: Optional[datetime] = None

    


# Update schema for evaluations
class EvaluationUpdate(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None


class ReceiptResponse(BaseModel):
    id: int
    filename: str
    status: ReceiptStatus
    extracted_data: Optional[Dict[str, Any]] = None
    audit_decision: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    # Task tracking
    task_id: Optional[str] = None
    task_started_at: Optional[datetime] = None
    task_completed_at: Optional[datetime] = None
    task_error: Optional[str] = None
    task_retry_count: int = 0
    processing_duration_ms: Optional[int] = None
    extraction_progress: int = 0
    audit_progress: int = 0

    model_config = ConfigDict(from_attributes=True)


# Add these new schemas

class JobResponse(BaseModel):
    """Background job status response."""
    id: str
    job_type: str
    status: str
    progress: int
    payload: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    receipt_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# Add the AuditRead schema (add after ReceiptRead)

class AuditRead(BaseModel):
    """Audit decision read model."""
    receipt_id: int
    decision: Dict[str, Any]
    created_at: datetime
    
    class Config:
        from_attributes = True