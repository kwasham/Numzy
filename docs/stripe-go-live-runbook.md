# Stripe Billing Go-Live Runbook

Authoritative checklist for promoting Numzy billing from test to production.

## 1. Preconditions

- All blocking checklist items marked complete (see `Stripe_Checklist.md`).
- Tests green (backend + frontend billing suites).
- Sentry project receiving test events.

## 2. Configure Production Environment Variables

Mandatory:

- STRIPE*API_KEY=sk_live*...
- STRIPE*PUBLISHABLE_KEY=pk_live*...
- STRIPE_WEBHOOK_SECRETS=<primary,rotating>
- STRIPE*PRICE*\* IDs (monthly & yearly as applicable)
- RECONCILE_CRON_ENABLED=true (worker)
- RECONCILE_CRON_INTERVAL_SECONDS=420 (tune if needed)
- RECONCILE_CRON_LOOKAHEAD_SECONDS=900
- STRIPE_WEBHOOK_ALLOWED_EVENTS=(comma list matching pruning allowlist)

Optional:

- STRIPE_AUTOMATIC_TAX_ENABLED=true
- DRAMATIQ_PROMETHEUS_ENABLED=true

## 3. Webhook Endpoint

1. Create production webhook endpoint pointing to https URL `/billing/webhook`.
2. Capture new secret; append to STRIPE_WEBHOOK_SECRETS (keep old for rotation overlap).
3. Run pruning script (dry-run then apply):

   ```bash
   python -m backend.scripts.stripe_prune_webhooks --endpoint we_xxxx
   python -m backend.scripts.stripe_prune_webhooks --endpoint we_xxxx --apply
   ```

4. Confirm only allowlist events remain.

## 4. Catalog Validation

- For each plan (personal, pro, business) and interval (monthly/yearly) ensure live Price IDs env vars present.
- Run a dry API call in prod shell: `/billing/catalog` -> verify prices & intervals.

## 5. Customer Portal Configuration

- In Dashboard: enable plan switching, payment method updates, invoices, cancellation (no proration credit on downgrade mid-cycle).
- Record Portal configuration ID (if necessary) and test with `/billing/portal`.

## 6. Plan Change Matrix (Manual QA)

For a real test customer (no real card charges where possible use test clock / sample card in live restricted environment):

| Case               | Steps                       | Expected                                           |
| ------------------ | --------------------------- | -------------------------------------------------- |
| New subscription   | Checkout -> Pro monthly     | Active, invoice paid, plan=pro                     |
| Upgrade            | Personal -> Pro             | Immediate invoice (prorated/upgrade)               |
| Downgrade schedule | Pro -> Personal             | cancel_at_period_end True + metadata.pending_plan  |
| Reconciliation     | Wait near renewal           | Downgrade applied before period end (cancel unset) |
| SCA required       | Use 3DS card                | requires_action banner + completion flow           |
| Past due           | Failing card -> update card | past_due banner then resolves after update         |
| Portal downgrade   | Use Portal to downgrade     | Reflected in status endpoint                       |
| Cancel             | Portal cancel               | plan downgraded appropriately                      |

## 7. Metrics & Observability

Verify presence in Sentry/metrics backend:

- stripe.webhook.received / duplicate / ignored / invalid_signature
- stripe.subscription.preview / change / plan.changed / downgrade_scheduled / downgrade.applied
- stripe.subscription.reconcile.run (completed, applied counts)
- stripe.subscription.change.error (ideally zero)
- invoice.paid / invoice.failed / invoice.action_required
- stripe.dunning.entered / stripe.dunning.recovered
- stripe.sca.entered / stripe.sca.completed

## 8. Alerts (Set Up)

- High error rate on change.error.
- Reconcile run applied spike threshold (e.g., >50 in run) or consecutive errors.
- Invoice failure % above baseline.

## 9. Dunning & SCA Simulation

- Trigger invoice.payment_failed (replace card with failing test token) -> banner -> update to working card.
- Trigger payment_action_required (3DS) -> banner & completion.

## 10. Tax & Address (if enabled)

- Submit address via Address Element; confirm persisted & Stripe Customer updated.
- Stripe Tax calculation present on test invoice (if enabled).

## 11. Wallets (if enabling at launch)

- Register Apple Pay domain (verify file served from /.well-known/apple-developer-merchantid-domain-association).
- Enable Apple & Google Pay in Dashboard + check Express Checkout renders in production.

## 12. Rollback Plan

If critical issue appears:

1. Disable RECONCILE_CRON_ENABLED (env) and restart worker (halts automated downgrades).
2. Revert deployment to last known good image tag.
3. If webhook malfunction: temporarily remove endpoint in Dashboard (Stripe will queue events for a short time) and fix.
4. Use `customer.subscription.update` via Stripe Dashboard for manual corrections.

## 13. Post-Launch Monitoring (First 24h)

- Track new subscription success rate.
- Monitor reconcile.applied counts vs expected downgrades.
- Inspect any change.error occurrences and resolve.

## 14. Sign-off

- Engineering lead approval.
- Product owner acknowledgement.
- Sentry dashboard link & metrics snapshot archived.

---

Maintained alongside `Stripe_Checklist.md`. Update this runbook after any material billing workflow change.
