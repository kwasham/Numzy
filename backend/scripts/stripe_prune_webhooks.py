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

# Align with events explicitly handled or queued in webhook handler:
# - checkout.session.completed (checkout linking)
# - customer.subscription.* (plan / status reconciliation)
# - invoice.payment_succeeded & invoice.paid (Stripe may emit either depending on API version)
# - invoice.payment_failed (dunning enter)
# - invoice.payment_action_required (SCA enter)
# - customer.updated (customer email / metadata sync)
DEFAULT_ALLOWED = [
    'checkout.session.completed',
    'customer.subscription.created',
    'customer.subscription.updated',
    'customer.subscription.deleted',
    'invoice.paid',
    'invoice.payment_succeeded',
    'invoice.payment_failed',
    'invoice.payment_action_required',
    'customer.updated',
]

def main():
    parser = argparse.ArgumentParser(description='Prune Stripe webhook endpoint events')
    parser.add_argument('--endpoint', required=True, help='Webhook endpoint ID (we_...)')
    parser.add_argument('--allowed', nargs='*', default=DEFAULT_ALLOWED, help='Allowed event types')
    parser.add_argument('--apply', action='store_true', help='Apply changes (otherwise dry-run)')
    parser.add_argument('--print-diff', action='store_true', help='Print a machine-readable JSON diff summary')
    parser.add_argument('--audit-json', help='Write full before/after JSON snapshot to file (dry-run safe)')
    parser.add_argument('--simulate-events', help='Path to JSON list of observed event types to diff (dry-run aid)')
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

    current_sorted = sorted(current)
    allowed_sorted = sorted(allowed)
    print('Current events:', current_sorted)
    print('Allowed target :', allowed_sorted)
    if args.print_diff:
        import json as _json
        diff_obj = {
            'endpoint': args.endpoint,
            'current': current_sorted,
            'target': allowed_sorted,
            'add': sorted(to_add),
            'remove': sorted(to_remove),
            'unchanged': sorted(current & allowed),
            'apply': bool(args.apply),
        }
        print('DIFF_JSON:', _json.dumps(diff_obj, separators=(',', ':')))

    if args.simulate_events:
        import json as _json
        try:
            with open(args.simulate_events) as f:
                observed = set(_json.load(f))
            missing_but_observed = sorted(observed - allowed)
            allowed_unused = sorted(allowed - observed)
            print('Simulation observed events:', sorted(observed))
            print('Observed NOT in allowlist (would be filtered):', missing_but_observed)
            print('Allowlist events not yet observed (ensure needed):', allowed_unused)
            if args.print_diff:
                sim = {
                    'observed': sorted(observed),
                    'observed_not_allowed': missing_but_observed,
                    'allowed_not_observed': allowed_unused,
                }
                print('SIM_JSON:', _json.dumps(sim, separators=(',', ':')))
        except Exception as e:  # pragma: no cover
            print('Failed simulation load:', e, file=sys.stderr)

    if args.audit_json:
        try:
            import json as _json
            with open(args.audit_json, 'w') as f:
                _json.dump({
                    'endpoint': args.endpoint,
                    'current': current_sorted,
                    'target': allowed_sorted,
                }, f, indent=2)
            print(f'Audit snapshot written to {args.audit_json}')
        except Exception as e:  # pragma: no cover
            print('Failed writing audit snapshot:', e, file=sys.stderr)

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
