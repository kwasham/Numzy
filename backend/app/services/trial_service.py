from __future__ import annotations

import datetime as dt
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F401 (reserved for future async variants)
from app.models.tables import User
from app.models.enums import PlanType
from app.core.observability import sentry_metric_inc, sentry_breadcrumb  # best-effort metrics

DEFAULT_TRIAL_DAYS = 14

class TrialService:
    """Helpers for starting and evaluating user trials and usage counts.

    Slice 1 responsibilities:
      - Ensure a trial window for Personal users who have not subscribed yet.
      - Reset monthly receipt counters at month boundary.
      - Increment usage and enforce limit (limit enforcement still resides in upload route for now).
    """

    def __init__(self, trial_days: int = DEFAULT_TRIAL_DAYS):
        self.trial_days = trial_days

    def ensure_trial(self, user: User, now: dt.datetime | None = None) -> bool:
        """Start a trial window for a newly onboarded user if they have never had one.

        Previous behaviour restricted trials to FREE plan users; the new model grants a trial
        to any user without an existing active/trialing subscription who has never started one.

        Heuristic: if user.trial_started_at is null and subscription_status NOT in (active, trialing),
        start a trial. This keeps us database‑only (no live Stripe calls here) and lets webhook
        reconciliation update subscription_status asynchronously.

        Returns True if a trial was started.
        """
        now = now or dt.datetime.utcnow()
        if user.trial_started_at:
            return False  # already has (or had) a trial
        status = (getattr(user, "subscription_status", None) or "").lower()
        if status in ("active", "trialing"):
            return False  # already subscribed; do not start new trial
        # Start trial
        user.trial_started_at = now
        user.trial_ends_at = now + dt.timedelta(days=self.trial_days)
        try:  # observability (non‑PII)
            sentry_metric_inc("trial.started")
            sentry_breadcrumb(
                category="trial",
                message="trial.started",
                data={
                    "days": self.trial_days,
                    "ends_at": user.trial_ends_at.isoformat() if user.trial_ends_at else None,
                },
            )
        except Exception:
            pass
        return True

    def is_trial_active(self, user: User, now: dt.datetime | None = None) -> bool:
        now = now or dt.datetime.utcnow()
        if not user.trial_started_at or not user.trial_ends_at:
            return False
        return user.trial_started_at <= now < user.trial_ends_at

    def maybe_reset_monthly_counter(self, user: User, now: dt.datetime | None = None) -> bool:
        """Reset the in-row monthly counter when entering a new calendar month.

        Emits metrics when a reset occurs.
        """
        now = now or dt.datetime.utcnow()
        reset = False
        previous_count = getattr(user, "monthly_receipt_count", None)
        if not user.last_receipt_reset_at:
            user.last_receipt_reset_at = now
            user.monthly_receipt_count = 0
            reset = True
        else:
            if (user.last_receipt_reset_at.year, user.last_receipt_reset_at.month) != (now.year, now.month):
                user.last_receipt_reset_at = now
                user.monthly_receipt_count = 0
                reset = True
        if reset:
            try:
                sentry_metric_inc("usage.monthly.reset")
                sentry_breadcrumb(
                    category="usage",
                    message="monthly.reset",
                    data={
                        "previous_count": previous_count,
                        "reset_month": f"{now.year:04d}-{now.month:02d}",
                    },
                )
            except Exception:
                pass
        return reset

    def increment_usage(self, user: User) -> None:
        if user.monthly_receipt_count is None:
            user.monthly_receipt_count = 0
        user.monthly_receipt_count += 1
