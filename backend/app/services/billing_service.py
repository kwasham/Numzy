"""Billing service stub for subscription and metered usage.

The billing service is responsible for enforcing plan limits,
charging users for overage and interfacing with a payment provider
such as Stripe. In this example implementation the service does
nothing but return fixed allowance values. Replace these
implementations with calls to Stripe's metered billing APIs or
another billing provider when deploying in production.
"""

from typing import Tuple

from app.models.enums import PlanType


class BillingService:
    """Stub billing service providing quota and limit information."""

    DEFAULT_QUOTAS = {
    PlanType.FREE: 50,
    PlanType.PERSONAL: 100,
    PlanType.PRO: 500,
        PlanType.BUSINESS: 5000,
        PlanType.ENTERPRISE: float("inf"),
    }

    def get_monthly_quota(self, plan: PlanType) -> float:
        """Return the maximum number of receipts allowed per month for a plan."""
        return self.DEFAULT_QUOTAS.get(plan, 0)

    def should_charge_overage(self, plan: PlanType, usage: int) -> bool:
        """Determine if usage has exceeded the plan's monthly quota."""
        limit = self.get_monthly_quota(plan)
        return usage > limit if limit != float("inf") else False

    def record_usage(self, user_id: int, count: int) -> None:
        """Record usage for billing. In this stub no operation is performed."""
        # In a real implementation you would increment a usage counter in
        # your billing system or database. This function intentionally
        # does nothing and always succeeds.
        return