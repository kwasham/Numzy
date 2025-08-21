"""Simple configuration management.

This module defines a ``Settings`` class that reads configuration
values from environment variables and provides sensible defaults.
It avoids depending on ``pydantic-settings`` so that the API can
run in constrained environments without extra dependencies. If
``.env`` support is needed you can implement it here by reading the
file manually or using ``dotenv``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv, find_dotenv

# Load environment variables, preferring the repo root .env over a backend/.env.
# Resolve repo root as ../../../ from this file: backend/app/core/config.py -> repo root
_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[3]
_ROOT_ENV = _REPO_ROOT / ".env"

# Build a preference-ordered list of .env files to load
_candidate_envs: list[str] = []
if _ROOT_ENV.exists():
    _candidate_envs.append(str(_ROOT_ENV))

# Fallback: whatever python-dotenv discovers from CWD (may be backend/.env when running worker)
_FOUND_ENV = find_dotenv()  # uses current working directory
if _FOUND_ENV and _FOUND_ENV not in _candidate_envs:
    _candidate_envs.append(_FOUND_ENV)

# As a last resort, allow a local .env in the module tree (not recommended)
_LOCAL_ENV = (_THIS_FILE.parent.parent.parent / ".env").as_posix()  # backend/.env
if os.path.exists(_LOCAL_ENV) and _LOCAL_ENV not in _candidate_envs:
    _candidate_envs.append(_LOCAL_ENV)

# Load in order without overriding already-set vars
for _env_path in _candidate_envs:
    load_dotenv(dotenv_path=_env_path, override=False)

class Settings(BaseSettings):
    """Application settings."""
    # pydantic-settings v2 style configuration
    model_config = SettingsConfigDict(
        # Provide the same preference order to pydantic-settings env loader
        env_file=tuple(_candidate_envs) if _candidate_envs else (".env",),
        case_sensitive=True,
        extra="allow",
    )
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Numzy Receipt Processing"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    
    # Database
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Storage
    STORAGE_BACKEND: str = Field(default="minio", env="STORAGE_BACKEND")
    MINIO_ENDPOINT: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(default="minioadmin", env="MINIO_SECRET_KEY")
    MINIO_BUCKET_NAME: str = Field(default="receipts", env="MINIO_BUCKET_NAME")
    MINIO_USE_SSL: bool = Field(default=False, env="MINIO_USE_SSL")
    
    # Auth
    DEV_AUTH_BYPASS: bool = Field(default=True, env="DEV_AUTH_BYPASS")
    CLERK_SECRET_KEY: Optional[str] = Field(default=None, env="CLERK_SECRET_KEY")
    
    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".webp"}
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="BACKEND_CORS_ORIGINS"
    )
    
    # Additional fields that might be in .env
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    STORAGE_DIRECTORY: str = Field(default="./storage", env="STORAGE_DIRECTORY")
    TEST_USER_JWT: Optional[str] = Field(default=None, env="TEST_USER_JWT")
    DRAMATIQ_BROKER_URL: Optional[str] = Field(default=None, env="DRAMATIQ_BROKER_URL")
    DRAMATIQ_PROMETHEUS_ENABLED: bool = Field(default=False, env="DRAMATIQ_PROMETHEUS_ENABLED")
    DRAMATIQ_PROMETHEUS_ADDR: str = Field(default="127.0.0.1", env="DRAMATIQ_PROMETHEUS_ADDR")
    DRAMATIQ_PROMETHEUS_PORT: int = Field(default=9191, env="DRAMATIQ_PROMETHEUS_PORT")
    MCP_URL: Optional[str] = Field(default=None, env="MCP_URL")
    SECRET_KEY: str = Field(default="changeme", env="SECRET_KEY")
    STRIPE_API_KEY: Optional[str] = Field(default=None, env="STRIPE_API_KEY")
    NEXT_PUBLIC_API_URL: Optional[str] = Field(default=None, env="NEXT_PUBLIC_API_URL")
    # Frontend base URL used for Stripe redirects
    FRONTEND_BASE_URL: str = Field(default="http://localhost:3000", env="FRONTEND_BASE_URL")
    # Dev DB fallback (fail fast by default)
    DB_DEV_FALLBACK_SQLITE: bool = Field(default=False, env="DB_DEV_FALLBACK_SQLITE")
    
    # Sentry
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.0, env="SENTRY_TRACES_SAMPLE_RATE")
    SENTRY_PROFILES_SAMPLE_RATE: float = Field(default=0.0, env="SENTRY_PROFILES_SAMPLE_RATE")
    # Optional Sentry release name to tag backend/worker events consistently with frontend
    SENTRY_RELEASE: Optional[str] = Field(default=None, env="SENTRY_RELEASE")
    
    # Stripe
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRET")
    # Comma-separated list of webhook secrets to support rotation seamlessly
    STRIPE_WEBHOOK_SECRETS: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_SECRETS")
    # Optional: allowlist of webhook event types to process (supports patterns like invoice.*)
    STRIPE_WEBHOOK_ALLOWED_EVENTS: Optional[str] = Field(default=None, env="STRIPE_WEBHOOK_ALLOWED_EVENTS")
    # Optional: known price IDs to map to plans
    STRIPE_PRICE_PRO_MONTHLY: Optional[str] = Field(default=None, env="STRIPE_PRICE_PRO_MONTHLY")
    STRIPE_PRICE_PRO_YEARLY: Optional[str] = Field(default=None, env="STRIPE_PRICE_PRO_YEARLY")
    STRIPE_PRICE_TEAM_MONTHLY: Optional[str] = Field(default=None, env="STRIPE_PRICE_TEAM_MONTHLY")
    # Optional: prefer price.lookup_key instead of hard-coded IDs
    STRIPE_LOOKUP_PRO_MONTHLY: Optional[str] = Field(default=None, env="STRIPE_LOOKUP_PRO_MONTHLY")
    STRIPE_LOOKUP_PRO_YEARLY: Optional[str] = Field(default=None, env="STRIPE_LOOKUP_PRO_YEARLY")
    STRIPE_LOOKUP_TEAM_MONTHLY: Optional[str] = Field(default=None, env="STRIPE_LOOKUP_TEAM_MONTHLY")
    # Optional: Stripe Billing Portal configuration ID
    STRIPE_PORTAL_CONFIGURATION_ID: Optional[str] = Field(default=None, env="STRIPE_PORTAL_CONFIGURATION_ID")
    # Optional: enable Stripe automatic tax on subscriptions/checkout
    STRIPE_AUTOMATIC_TAX_ENABLED: bool = Field(default=False, env="STRIPE_AUTOMATIC_TAX_ENABLED")
    
    # Legacy Config class no longer required; using model_config above

settings = Settings()

# Convenience: computed helpers
def get_webhook_secret_list() -> list[str]:
    """Return list of webhook secrets for signature verification.

    Order matters; the first secret is treated as primary.
    """
    secrets: list[str] = []
    if settings.STRIPE_WEBHOOK_SECRETS:
        secrets.extend([s.strip() for s in settings.STRIPE_WEBHOOK_SECRETS.split(",") if s.strip()])
    if settings.STRIPE_WEBHOOK_SECRET and settings.STRIPE_WEBHOOK_SECRET.strip():
        # Append single secret if not already present
        if settings.STRIPE_WEBHOOK_SECRET.strip() not in secrets:
            secrets.append(settings.STRIPE_WEBHOOK_SECRET.strip())
    return secrets

# Reduce SQLAlchemy logging verbosity
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)