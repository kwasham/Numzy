#!/usr/bin/env python
"""Prune Stripe webhook endpoint events to a curated allowlist.

Usage:
  python -m backend.scripts.stripe_prune_webhooks --endpoint <WEHOOK_ENDPOINT_ID> \
      --allowed checkout.session.completed customer.subscription.created \
      customer.subscription.updated customer.subscription.deleted invoice.paid \
      invoice.payment_failed invoice.payment_action_required customer.updated

Requires STRIPE_API_KEY env var. Dry-run by default; pass --apply to perform updates.
"""
from __future__ import annotations
import os
import argparse
import sys
import logging

try:
    import stripe  # type: ignore
except Exception as e:  # pragma: no cover
    print("Stripe library not installed", e, file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

DEFAULT_ALLOWED = [
    'checkout.session.completed',
    'customer.subscription.created',
    'customer.subscription.updated',
    'customer.subscription.deleted',
    'invoice.paid',
    'invoice.payment_failed',
    'invoice.payment_action_required',
    'customer.updated',
]

def main():
    parser = argparse.ArgumentParser(description='Prune Stripe webhook endpoint events')
    parser.add_argument('--endpoint', required=True, help='Webhook endpoint ID (we_...)')
    parser.add_argument('--allowed', nargs='*', default=DEFAULT_ALLOWED, help='Allowed event types')
    parser.add_argument('--apply', action='store_true', help='Apply changes (otherwise dry-run)')
    args = parser.parse_args()

    api_key = os.getenv('STRIPE_API_KEY')
    if not api_key:
        print('STRIPE_API_KEY env var required', file=sys.stderr)
        return 2
    stripe.api_key = api_key  # type: ignore

    try:
        ep = stripe.WebhookEndpoint.retrieve(args.endpoint)  # type: ignore
    except Exception as e:  # pragma: no cover
        print('Failed to retrieve endpoint:', e, file=sys.stderr)
        return 3

    current = set(ep.get('enabled_events', []) if isinstance(ep, dict) else [])
    allowed = set(args.allowed)
    to_remove = current - allowed
    to_add = allowed - current

    print('Current events:', sorted(current))
    print('Allowed target :', sorted(allowed))
    if not to_remove and not to_add:
        print('No changes needed.')
        return 0

    print('Will remove:', sorted(to_remove))
    print('Will add   :', sorted(to_add))

    if not args.apply:
        print('Dry-run complete. Re-run with --apply to modify endpoint.')
        return 0

    new_events = sorted(allowed)
    try:
        updated = stripe.WebhookEndpoint.modify(args.endpoint, enabled_events=new_events)  # type: ignore
        print('Updated endpoint events:', updated.get('enabled_events'))
    except Exception as e:  # pragma: no cover
        print('Failed to update endpoint:', e, file=sys.stderr)
        return 4
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
