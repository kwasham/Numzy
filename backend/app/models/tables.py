"""SQLAlchemy ORM models for the receipt processing API.

These models define the relational database schema used by the
application. Relationships are defined for one-to-many and
many-to-many associations. Enumerated fields are stored as
strings using SQLAlchemy's native Enum type. JSON columns are
implemented using the built‑in JSON type where appropriate.

If you extend or modify these models remember to run alembic
migrations or call the ``init_db`` helper during development to
recreate the tables.
"""

from __future__ import annotations

import datetime as dt
from typing import Optional, List

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    Table,
    Text,
    JSON,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from .enums import PlanType, RuleType, ReceiptStatus, EvaluationStatus


class User(Base):
    """User account representing an individual using the service."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    # Stripe customer reference for billing webhooks (e.g., "cus_...")
    stripe_customer_id = Column(String, unique=True, nullable=True)
    name = Column(String, nullable=False)
    plan = Column(Enum(PlanType), nullable=False, default=PlanType.FREE)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)

    # Relationships
    receipts = relationship("Receipt", back_populates="owner")
    audit_rules = relationship("AuditRule", back_populates="owner")
    prompt_templates = relationship("PromptTemplate", back_populates="owner")
    evaluations = relationship("Evaluation", back_populates="owner")
    background_jobs = relationship("BackgroundJob", back_populates="user", cascade="all, delete-orphan")


class Organisation(Base):
    """Organisation or team consisting of multiple users."""

    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    plan = Column(Enum(PlanType), nullable=False, default=PlanType.BUSINESS)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)

    # Organisation members association table is defined below
    members = relationship("User", secondary="organisation_members", backref="organisations")
    receipts = relationship("Receipt", back_populates="organisation")
    audit_rules = relationship("AuditRule", back_populates="organisation")
    prompt_templates = relationship("PromptTemplate", back_populates="organisation")
    evaluations = relationship("Evaluation", back_populates="organisation")


# Many‑to‑many table linking users to organisations with optional role
organisation_members = Table(
    "organisation_members",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("organisation_id", Integer, ForeignKey("organisations.id"), primary_key=True),
    Column("role", String, default="member", nullable=False),
)


class Receipt(Base):
    """Uploaded receipt and associated processing results."""

    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    file_path = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    status = Column(Enum(ReceiptStatus), default=ReceiptStatus.PENDING, nullable=False)
    extracted_data = Column(JSON, nullable=True)
    audit_decision = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)

    # Add task tracking fields
    task_id = Column(String, nullable=True, index=True)  # Dramatiq message ID
    task_started_at = Column(DateTime(timezone=True), nullable=True)
    task_completed_at = Column(DateTime(timezone=True), nullable=True)
    task_error = Column(Text, nullable=True)
    task_retry_count = Column(Integer, default=0)
    processing_duration_ms = Column(Integer, nullable=True)

    # Add progress tracking
    extraction_progress = Column(Integer, default=0)  # 0-100
    audit_progress = Column(Integer, default=0)  # 0-100

    owner = relationship("User", back_populates="receipts")
    organisation = relationship("Organisation", back_populates="receipts")
    background_job = relationship("BackgroundJob", back_populates="receipt", uselist=False)


class AuditRule(Base):
    """User‑configured audit rule definition."""

    __tablename__ = "audit_rules"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    type = Column(Enum(RuleType), nullable=False)
    config = Column(JSON, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="audit_rules")
    organisation = relationship("Organisation", back_populates="audit_rules")


class PromptTemplate(Base):
    """Custom prompt templates for extraction, audit, evaluation or cost analysis."""

    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="prompt_templates")
    organisation = relationship("Organisation", back_populates="prompt_templates")


class Evaluation(Base):
    """Evaluation run that benchmarks extraction and audit models."""

    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    organisation_id = Column(Integer, ForeignKey("organisations.id"), nullable=True)
    model_name = Column(String, nullable=False)
    status = Column(Enum(EvaluationStatus), default=EvaluationStatus.CREATED, nullable=False)
    summary_metrics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow, nullable=False)

    owner = relationship("User", back_populates="evaluations")
    organisation = relationship("Organisation", back_populates="evaluations")
    items = relationship("EvaluationItem", back_populates="evaluation", cascade="all, delete-orphan")
    cost_analyses = relationship("CostAnalysis", back_populates="evaluation", cascade="all, delete-orphan")


class EvaluationItem(Base):
    """Individual item within an evaluation run."""

    __tablename__ = "evaluation_items"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), nullable=False)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=True)
    predicted_receipt_details = Column(JSON, nullable=False)
    predicted_audit_decision = Column(JSON, nullable=False)
    correct_receipt_details = Column(JSON, nullable=False)
    correct_audit_decision = Column(JSON, nullable=False)
    grader_scores = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)

    evaluation = relationship("Evaluation", back_populates="items")
    receipt = relationship("Receipt")


class CostAnalysis(Base):
    """Cost analysis linked to an evaluation run."""

    __tablename__ = "cost_analyses"

    id = Column(Integer, primary_key=True, index=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"), nullable=False)
    parameters = Column(JSON, nullable=False)
    result = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow, nullable=False)

    evaluation = relationship("Evaluation", back_populates="cost_analyses")


class BackgroundJob(Base):
    """Track background job status and progress."""
    __tablename__ = "background_jobs"
    
    id = Column(String, primary_key=True)  # Dramatiq message ID
    job_type = Column(String, nullable=False)  # e.g., "receipt_extraction"
    status = Column(String, nullable=False, default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    
    # Job metadata
    payload = Column(JSON)  # Store job arguments
    result = Column(JSON)  # Store job results
    error = Column(Text)  # Error message if failed
    
    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user_id = Column(Integer, ForeignKey("users.id"))
    receipt_id = Column(Integer, ForeignKey("receipts.id"))
    
    user = relationship("User", back_populates="background_jobs")
    receipt = relationship("Receipt", back_populates="background_job")