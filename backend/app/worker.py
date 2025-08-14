"""Dramatiq worker configuration.

This module configures the Dramatiq broker and imports all tasks
so they are registered when the worker starts.

Run with:
    python -m dramatiq app.worker
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

"""Ensure environment is loaded from repo root .env when running via CLI."""
# Configure environment
os.environ.setdefault("ENV", "development")

# Load the repo root .env explicitly to avoid relying on CWD
repo_root = Path(__file__).resolve().parents[2]
root_env = repo_root / ".env"
if root_env.exists():
    load_dotenv(dotenv_path=str(root_env), override=False)

# Import settings first
from app.core.config import settings

# Optional Sentry for worker
try:
    import sentry_sdk
    _SENTRY_AVAILABLE = True
except Exception:
    _SENTRY_AVAILABLE = False

if _SENTRY_AVAILABLE and settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=float(settings.SENTRY_TRACES_SAMPLE_RATE or 0),
        profiles_sample_rate=float(settings.SENTRY_PROFILES_SAMPLE_RATE or 0),
        environment=settings.ENVIRONMENT,
    release=settings.SENTRY_RELEASE,
    )
    print("Sentry SDK initialized for worker")

# Propagate key env vars for libraries reading directly from os.environ
if settings.OPENAI_API_KEY:
    os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)
if settings.DATABASE_URL:
    os.environ.setdefault("DATABASE_URL", settings.DATABASE_URL)

# Configure Dramatiq broker
import dramatiq
from dramatiq.brokers.redis import RedisBroker

# Get Redis URL from settings
redis_url = os.getenv("DRAMATIQ_BROKER_URL", "redis://localhost:6379/0")
print(f"Configuring Dramatiq with Redis URL: {redis_url}")

# Create and configure broker
broker = RedisBroker(url=redis_url)
dramatiq.set_broker(broker)
print("Dramatiq broker configured successfully")

# Import tasks to register them
from app.core.tasks import extract_and_audit_receipt, run_evaluation  # noqa: F401

print("Tasks registered successfully")