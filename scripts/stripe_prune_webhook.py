#!/usr/bin/env python3
"""
Prune a Stripe webhook endpoint's enabled_events to a recommended minimal set.

Usage:
  python scripts/stripe_prune_webhook.py --endpoint WE_123...
  python scripts/stripe_prune_webhook.py --url https://api.example.com/stripe/webhook

Env:
  STRIPE_SECRET_KEY: Required. Your Stripe API secret key.

Options:
  --include-customer: Keep customer.* events (default true). Use --no-include-customer to exclude.
  --dry-run: Show what would change without applying (default true). Use --apply to modify.

Notes:
  - This script is idempotent. It prints before/after and exits non-zero on errors.
  - We do not store secrets; ensure STRIPE_SECRET_KEY is set in your shell.
"""

from __future__ import annotations
import argparse
import os
import sys
from typing import List, Optional

try:
    import stripe  # type: ignore
except Exception as e:
    print("Stripe SDK is required. Install with: pip install stripe", file=sys.stderr)
    raise

RECOMMENDED_EVENTS_BASE = [
    # Checkout
    "checkout.session.completed",
    "checkout.session.async_payment_succeeded",
    "checkout.session.async_payment_failed",
    # Subscriptions
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    # Invoices
    "invoice.created",
    "invoice.finalized",
    "invoice.payment_succeeded",
    "invoice.payment_failed",
    "invoice.payment_action_required",
]

CUSTOMER_EVENTS = [
    "customer.created",
    "customer.updated",
    "customer.deleted",
]


def resolve_endpoint_by_url(client: stripe, url: str) -> Optional[str]:
    endpoints = stripe.WebhookEndpoint.list(limit=100)
    for ep in endpoints.auto_paging_iter():
        if ep.get("url") == url:
            return ep.get("id")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", help="Webhook endpoint ID (e.g., we_123)")
    parser.add_argument("--url", help="Webhook endpoint URL to match (alternative to --endpoint)")
    parser.add_argument("--include-customer", dest="include_customer", action=argparse.BooleanOptionalAction, default=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", dest="apply", action="store_false", default=False, help="Do not apply changes (default)")
    group.add_argument("--apply", dest="apply", action="store_true", help="Apply the changes")
    args = parser.parse_args()

    secret = os.getenv("STRIPE_SECRET_KEY")
    if not secret:
        print("Missing STRIPE_SECRET_KEY in environment.", file=sys.stderr)
        return 2

    stripe.api_key = secret

    endpoint_id = args.endpoint
    if not endpoint_id and args.url:
        endpoint_id = resolve_endpoint_by_url(stripe, args.url)
        if not endpoint_id:
            print(f"No endpoint found with URL: {args.url}", file=sys.stderr)
            return 3

    if not endpoint_id:
        print("You must provide --endpoint or --url to identify the webhook endpoint.", file=sys.stderr)
        return 2

    ep = stripe.WebhookEndpoint.retrieve(endpoint_id)
    before_events: List[str] = list(ep.get("enabled_events") or [])

    target = list(RECOMMENDED_EVENTS_BASE)
    if args.include_customer:
        target.extend(CUSTOMER_EVENTS)

    # Ensure uniqueness and stable order
    seen = set()
    target_unique = [e for e in target if not (e in seen or seen.add(e))]

    print("Endpoint:", endpoint_id)
    print("URL:", ep.get("url"))
    print("Current events ({}):".format(len(before_events)))
    for e in before_events:
        print("  -", e)

    print("\nTarget events ({}):".format(len(target_unique)))
    for e in target_unique:
        print("  -", e)

    if set(before_events) == set(target_unique):
        print("\nNo changes needed. Endpoint already matches target set.")
        return 0

    if not args.apply:
        print("\nDry run (no changes applied). Use --apply to update the endpoint.")
        return 0

    updated = stripe.WebhookEndpoint.modify(endpoint_id, enabled_events=target_unique)
    after_events: List[str] = list(updated.get("enabled_events") or [])

    print("\nUpdated events ({}):".format(len(after_events)))
    for e in after_events:
        print("  -", e)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
