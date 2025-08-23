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

from app.core.observability import init_sentry
try:  # optional import for spans
    import sentry_sdk  # type: ignore
except Exception:  # pragma: no cover
    sentry_sdk = None  # type: ignore

if init_sentry("worker"):
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
from app.core.tasks import extract_and_audit_receipt, run_evaluation, reconcile_pending_subscription_downgrades  # noqa: F401

print("Reconciliation actor registered: reconcile_pending_subscription_downgrades")

print("Tasks registered successfully")

# Optional lightweight cron loop (avoid external scheduler) – enabled via env RECONCILE_CRON_ENABLED=true
import threading, time

def _maybe_start_reconcile_cron():  # pragma: no cover - simple orchestrator
    if os.getenv("RECONCILE_CRON_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return
    interval = int(os.getenv("RECONCILE_CRON_INTERVAL_SECONDS", "420"))  # default 7m
    lookahead = int(os.getenv("RECONCILE_CRON_LOOKAHEAD_SECONDS", "900"))  # 15m lookahead
    batch_limit = int(os.getenv("RECONCILE_CRON_BATCH_LIMIT", "200"))
    def loop():
        while True:
            try:
                print(f"[cron] enqueue reconcile_pending_subscription_downgrades interval={interval}s lookahead={lookahead}s batch_limit={batch_limit}")
                reconcile_pending_subscription_downgrades.send(lookahead_seconds=lookahead, batch_limit=batch_limit)
            except Exception as e:  # pragma: no cover
                print(f"[cron] failed to enqueue reconcile task: {e}")
            time.sleep(interval)
    t = threading.Thread(target=loop, name="reconcile-cron", daemon=True)
    t.start()
    print(f"Reconciliation cron loop started (interval={interval}s)")

_maybe_start_reconcile_cron()