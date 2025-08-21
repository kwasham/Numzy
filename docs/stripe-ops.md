# Stripe Ops — Webhooks pruning and Observability

This guide helps you: (1) prune Stripe Dashboard webhook events to reduce noise, and (2) build Sentry dashboards from our emitted metrics.

Last updated: 2025-08-21

## 1) Prune webhook events in Stripe Dashboard

Target set of events (minimally sufficient for subscriptions + Checkout):

- checkout.session.\*
- customer.subscription.\*
- invoice.\*
- customer.\* (created/updated/deleted for hygiene; optional if you don’t rely on customer updates)

Steps:

1. In Stripe Dashboard → Developers → Webhooks → your endpoint.
2. Click “Select events” and remove everything not listed above.
3. Save. Deliveries will immediately reflect the narrowed set.

Safety net on backend:

- We enforce an allowlist via STRIPE_WEBHOOK_ALLOWED_EVENTS. Non‑matching events return 2xx and increment metric `stripe.webhook.ignored`.
- We emit `stripe.webhook.received` for every intake to visualize effectiveness of pruning.

Verification:

- Use Stripe CLI: `stripe listen --forward-to <your-endpoint>` and trigger test events to ensure only allowed events reach processing (others should be counted as ignored if sent).
- In Dashboard → Webhooks → your endpoint → Recent events: confirm high 2xx rate and expected event types.

## 2) Sentry dashboards from custom metrics

We emit the following counters (namespaced):

- stripe.webhook.received
- stripe.webhook.queued
- stripe.webhook.duplicate
- stripe.webhook.invalid_signature
- stripe.webhook.ignored
- stripe.checkout.completed
- stripe.subscription.event (tags include event_type and subscription_status)
- stripe.invoice.paid / stripe.invoice.failed / stripe.invoice.action_required (tags include invoice_id and price_id)

Suggested widgets:

- Webhook intake overview: Timeseries stacked of received vs queued vs ignored vs duplicate.
- Reliability: Invalid signature count (timeseries) with threshold alert.
- Subscription health: Breakdown by subscription_status from `stripe.subscription.event`.
- Invoice outcomes: Paid vs Failed vs Action Required, 7d trend.

Alerts (examples):

- If `stripe.webhook.invalid_signature` > 0 in 10m, send alert to on‑call.
- If `stripe.invoice.failed` increases > N in 1h, route to billing channel.

Notes:

- Keep tags PII‑safe. We tag subscription/invoice/price IDs and subscription status, but not customer PII.
- Correlate metrics with traces by filtering for route names containing `stripe_webhook` / `billing`.

## 3) Automatic tax readiness

- Backend flag STRIPE_AUTOMATIC_TAX_ENABLED enables `automatic_tax: { enabled: true }` for both Checkout and Elements subscription create.
- If enabled, add Address collection in the frontend (Stripe Address Element) to improve tax accuracy.

## 4) Runbook — quick checks

- Webhooks: 2xx rate high, duplicates near zero, invalid signature zero, ignored trending down after pruning.
- Subscriptions: Events flowing on create/update/delete; invoice paid ratios healthy.
- Recovery UX: Past_due and requires_action banners render, PM update flow works.
