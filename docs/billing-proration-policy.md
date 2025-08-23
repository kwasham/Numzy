# Billing Proration Policy

This document codifies Numzy's subscription plan change behaviors for transparency and to anchor automated tests.

## Principles

- Upgrades should unlock value immediately and bill (or invoice) the user for the prorated difference right away to avoid under‑charging.
- Downgrades should not grant immediate credit; instead they take effect at the next renewal to avoid mid‑cycle feature confusion.
- Lateral or no‑op changes (same plan/price) should be a no‑cost, no‑op (difference = 0) and avoid Stripe modification calls beyond preview.

## Behaviors

| Scenario             | Example         | Stripe action                                                      | proration_behavior | Immediate invoice?            | Metadata            | cancel_at_period_end        |
| -------------------- | --------------- | ------------------------------------------------------------------ | ------------------ | ----------------------------- | ------------------- | --------------------------- |
| Upgrade              | Personal -> Pro | Modify subscription item price to target                           | create_invoice     | Yes (captures prorated delta) | none                | False                       |
| Downgrade (deferred) | Pro -> Personal | Mark subscription cancel_at_period_end & set metadata.pending_plan | none               | No                            | pending_plan=target | True (until reconciliation) |
| No-op                | Pro -> Pro      | No modify (preview returns difference 0)                           | n/a                | No                            | none                | Unchanged                   |

## Edge Cases

- Interval Switch Upwards (monthly -> yearly, same plan): treat as upgrade only if yearly price > monthly \* remaining cycles; currently we opt for create_invoice for interval upgrades that increase unit_amount, else schedule at period end (future enhancement— not yet implemented/tested).
- Failed Upgrade modify: emits `stripe.subscription.change.error` metric + breadcrumb; client sees 500 error.
- Missing target price for downgrade: skip scheduling (400) so user can report misconfiguration.

## Tests Mapping

| Test                                             | Scenario           | Assertion                                                                     |
| ------------------------------------------------ | ------------------ | ----------------------------------------------------------------------------- |
| test_preview_upgrade                             | Upgrade preview    | difference > 0, is_upgrade True                                               |
| test_preview_downgrade                           | Downgrade preview  | difference < 0, is_upgrade False                                              |
| test_preview_no_op_same_plan                     | No-op              | difference 0, is_upgrade False                                                |
| test_change_upgrade_immediate_proration          | Upgrade change     | proration_behavior=create_invoice, cancel_at_period_end False                 |
| test_change_deferred_downgrade_sets_pending_plan | Downgrade schedule | cancel_at_period_end True, proration_behavior none, metadata.pending_plan set |
| test_reconciliation_applies_and_clears_metadata  | Downgrade apply    | cancel_at_period_end False, metadata.pending_plan cleared                     |

## Operational Notes

- Reconciliation window defaults: lookahead 15m; cron interval 7m (tunable by env). This ensures downgrade applied before Stripe finalizes renewal invoice.
- If reconciliation applies late (after invoice), we may incur one extra cycle at old price; monitor applied count anomalies.

## Future Improvements

- Interval switching nuanced handling.
- Mid-cycle add-ons (per-seat) with proportional billing.
- Proactive notification to user when downgrade scheduled (email + in-app toast).
