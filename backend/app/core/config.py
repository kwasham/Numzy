"""Simple configuration management.

This module defines a ``Settings`` class that reads configuration
values from environment variables and provides sensible defaults.  It
avoids depending on ``pydantic-settings`` so that the API can run in
constrained environments without extra dependencies.  ``.env`` support
is implemented by loading files from the repository root in a defined
order.  You can override any value via environment variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv, find_dotenv

# -----------------------------------------------------------------------------
# .env loading
#
# Prefer a .env in the repository root but allow fallback to whatever
# python-dotenv discovers from the current working directory.  As a last
# resort, a .env alongside this module may be used.  Files are loaded in
# order without overriding already-set variables.

_THIS_FILE = Path(__file__).resolve()
_REPO_ROOT = _THIS_FILE.parents[3]
_ROOT_ENV = _REPO_ROOT / ".env"

_candidate_envs: list[str] = []
if _ROOT_ENV.exists():
    _candidate_envs.append(str(_ROOT_ENV))

_FOUND_ENV = find_dotenv()
if _FOUND_ENV and _FOUND_ENV not in _candidate_envs:
    _candidate_envs.append(_FOUND_ENV)

_LOCAL_ENV = (_THIS_FILE.parent.parent.parent / ".env").as_posix()
if os.path.exists(_LOCAL_ENV) and _LOCAL_ENV not in _candidate_envs:
    _candidate_envs.append(_LOCAL_ENV)

for _env_path in _candidate_envs:
    load_dotenv(dotenv_path=_env_path, override=False)


class Settings(BaseSettings):
    """Application settings.

    Values are loaded from the environment with sensible defaults.  Any
    attribute defined here can be overridden by setting the corresponding
    environment variable.  See the README for a list of important variables.
    """

    model_config = SettingsConfigDict(
        env_file=tuple(_candidate_envs) if _candidate_envs else (".env",),
        case_sensitive=True,
        extra="allow",
    )

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Numzy Receipt Processing"
    ENVIRONMENT: str = Field(default="development")

    # Database
    DATABASE_URL: Optional[str] = Field(default=None)
    # Optional authenticated database URL for Neon RLS.  When provided, the
    # application will prefer this connection string for runtime queries.
    # Falls back to `DATABASE_URL` when unset.  Use this in conjunction
    # with Neon row-level security and pg_session_jwt.
    DATABASE_AUTHENTICATED_URL: Optional[str] = Field(default=None)

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # OpenAI
    OPENAI_API_KEY: Optional[str] = Field(default=None)

    # Storage
    STORAGE_BACKEND: str = Field(default="minio")
    MINIO_ENDPOINT: str = Field(default="localhost:9000")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin")
    MINIO_SECRET_KEY: str = Field(default="minioadmin")
    MINIO_BUCKET_NAME: str = Field(default="receipts")
    MINIO_USE_SSL: bool = Field(default=False)

    # Auth
    # Disable auth bypass by default for improved security.  Override in .env
    # or via environment variable only when running locally.
    DEV_AUTH_BYPASS: bool = Field(default=False)
    CLERK_SECRET_KEY: Optional[str] = Field(default=None)
    # Additional Clerk settings allow custom JWKS and API endpoints plus claim
    # verification.  These correspond to the values used in `app.core.security`.
    CLERK_API_URL: Optional[str] = Field(default="https://api.clerk.com/v1")
    CLERK_JWKS_URL: Optional[str] = Field(default=None)
    CLERK_JWT_AUDIENCE: Optional[str] = Field(default=None)
    CLERK_JWT_ISSUER: Optional[str] = Field(default=None)

    # File Upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".webp"}

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
    )

    # Additional optional fields
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None)
    STORAGE_DIRECTORY: str = Field(default="./storage")
    TEST_USER_JWT: Optional[str] = Field(default=None)
    DRAMATIQ_BROKER_URL: Optional[str] = Field(default=None)
    DRAMATIQ_PROMETHEUS_ENABLED: bool = Field(default=False)
    DRAMATIQ_PROMETHEUS_ADDR: str = Field(default="127.0.0.1")
    DRAMATIQ_PROMETHEUS_PORT: int = Field(default=9191)
    MCP_URL: Optional[str] = Field(default=None, json_schema_extra={"env": "MCP_URL"})
    SECRET_KEY: str = Field(default="changeme")
    STRIPE_API_KEY: Optional[str] = Field(default=None)
    NEXT_PUBLIC_API_URL: Optional[str] = Field(default=None, json_schema_extra={"env": "NEXT_PUBLIC_API_URL"})
    # Frontend base URL used for Stripe redirects
    FRONTEND_BASE_URL: str = Field(default="http://localhost:3000")
    # Dev DB fallback (fail fast by default)
    DB_DEV_FALLBACK_SQLITE: bool = Field(default=False)

    # Sentry
    SENTRY_DSN: Optional[str] = Field(default=None)
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=0.0)
    SENTRY_PROFILES_SAMPLE_RATE: float = Field(default=0.0)
    # Optional Sentry release name to tag backend/worker events consistently with frontend
    SENTRY_RELEASE: Optional[str] = Field(default=None)

    # Stripe
    STRIPE_WEBHOOK_SECRET: Optional[str] = Field(default=None)
    STRIPE_WEBHOOK_SECRETS: Optional[str] = Field(default=None)
    STRIPE_WEBHOOK_ALLOWED_EVENTS: Optional[str] = Field(default=None)
    STRIPE_PRICE_PRO_MONTHLY: Optional[str] = Field(default=None)
    STRIPE_PRICE_PRO_YEARLY: Optional[str] = Field(default=None)
    STRIPE_PRICE_TEAM_MONTHLY: Optional[str] = Field(default=None)
    STRIPE_PRICE_PERSONAL_MONTHLY: Optional[str] = Field(default=None)
    STRIPE_PRICE_BUSINESS_MONTHLY: Optional[str] = Field(default=None)
    STRIPE_LOOKUP_PRO_MONTHLY: Optional[str] = Field(default=None)
    STRIPE_LOOKUP_PRO_YEARLY: Optional[str] = Field(default=None)
    STRIPE_LOOKUP_TEAM_MONTHLY: Optional[str] = Field(default=None)
    STRIPE_LOOKUP_PERSONAL_MONTHLY: Optional[str] = Field(default=None)
    STRIPE_LOOKUP_BUSINESS_MONTHLY: Optional[str] = Field(default=None)
    STRIPE_PORTAL_CONFIGURATION_ID: Optional[str] = Field(default=None)
    STRIPE_AUTOMATIC_TAX_ENABLED: bool = Field(default=False)


# Instantiate global settings
settings = Settings()


def get_webhook_secret_list() -> list[str]:
    """Return list of webhook secrets for signature verification.

    Precedence:
    1. STRIPE_WEBHOOK_SECRETS (comma separated, ordered)
    2. Fallback to singular STRIPE_WEBHOOK_SECRET if set
    """
    secrets: list[str] = []
    if settings.STRIPE_WEBHOOK_SECRETS:
        secrets.extend([s.strip() for s in settings.STRIPE_WEBHOOK_SECRETS.split(",") if s.strip()])
    elif settings.STRIPE_WEBHOOK_SECRET:
        secrets.append(settings.STRIPE_WEBHOOK_SECRET.strip())
    return secrets