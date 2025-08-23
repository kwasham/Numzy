# Stripe Billing — Production Checklist (Numzy)

Purpose: a practical, production-hardening guide for our Stripe Billing integration across FastAPI backend and Next.js frontend. Use this document to track readiness and verify go-live steps.

Last updated: 2025-08-21

---

## High-level goals

- Reliable webhooks (verified, idempotent, async).
- Correct subscription lifecycle handling (SCA, failures, proration, cancel).
- Clean catalog management (lookup keys, hide unavailable tiers, yearly SKUs).
- Customer + payment method hygiene (default PM saved/updated, address/tax ready).
- Great checkout UX (Express Checkout, trials, clear error states, dark theme).
- Customer Portal wired to our catalog and behaviors.
- Secure keys/PCI posture; idempotency everywhere.
- Observability and tests for critical flows; go-live checklist complete.

---

## Quick wins (status)

- [x] Webhook de-dup: persist processed `event.id` and early-exit on duplicates (Redis TTL).
- [x] Idempotency: add `Idempotency-Key` on create calls (checkout session, Elements subscription).
- [x] Express Checkout wiring in UI (enable Apple/Google Pay after domain/HTTPS in prod).
- [x] Pricing by lookup keys: prefer lookup_key with fallback to env IDs.

Next quick wins

- [x] Frontend prompts for SCA/payment failure states.
- [ ] Register Apple/Google Pay (prod domain, HTTPS) and enable wallet buttons.
- [ ] Add Address Element and/or Stripe Tax configuration.

---

## Backend (FastAPI) — required items

### 1) Webhooks: security, reliability, async

- [x] Verify signatures against the raw request body; reject if invalid.
- [x] Return HTTP 2xx immediately (queued path)
- [x] Offload processing to Dramatiq (enqueue with inline fallback)
- [x] De-duplicate: persist processed `event.id` and skip repeats (Redis TTL; DB table optional)
- [x] Support secret rotation: allow multiple webhook secrets (comma-separated) and try each
  - Implemented via STRIPE_WEBHOOK_SECRETS with verification loop.
- [ ] Subscribe only to necessary events in Dashboard (reduce noise):
  - `checkout.session.*`, `customer.subscription.*`, `invoice.*`, `customer.*`
  - Backend safety net added: `STRIPE_WEBHOOK_ALLOWED_EVENTS` allowlist filters non-matching events server‑side and emits `stripe.webhook.ignored` metric; we also emit `stripe.webhook.received` for overall intake visibility.
  - Pruning script added: `backend/scripts/stripe_prune_webhooks.py` (dry-run by default, use --apply to modify Dashboard endpoint).

Files to touch

- `backend/app/api/routes/stripe_webhooks.py` (raw body verify, 2xx fast, enqueue, de-dup)
- `backend/app/core/config.py` (multiple secrets; env parsing)
- `backend/app/core/tasks.py` or `backend/app/worker.py` (Dramatiq jobs)
- Alembic migration for `stripe_webhook_events` (event_id unique, processed_at)
- Optional: `scripts/stripe_prune_webhook.py` — CLI to prune Dashboard webhook events to the recommended set.

Notes

- See: Stripe docs “Receive Stripe events in your webhook endpoint — Best practices”.
  - Verified: Async offload implemented via Dramatiq actor `process_stripe_event` (see `backend/app/core/tasks.py`) and enqueued in `backend/app/api/routes/stripe_webhooks.py`; tests cover enqueue path (`backend/tests/test_async_offload.py`).

### 2) Subscription lifecycle correctness

- [ ] On `invoice.payment_failed` → mark account “past_due” or similar; prompt to update PM.
- [ ] On `invoice.payment_action_required` → flag SCA required and guide user to complete.
  - Backend webhook now logs and flags these states; UI prompts still needed.
- [x] On `customer.subscription.created/updated` → set plan based on active price.
- [x] On `customer.subscription.deleted` or status=unpaid/canceled → downgrade safely.
- [ ] Consistent proration behavior for upgrades/downgrades (document policy).

Files to touch

- `backend/app/api/routes/stripe_webhooks.py`
- `backend/app/api/routes/billing.py` (status reconciliation already in place; extend for new states)

Refs

- “Using webhooks with subscriptions — Handle payment failures & requires_action”.

### 3) Pricing/catalog via lookup keys

- [x] Prefer Stripe Price `lookup_key`s with fallback to env price IDs.
  - Catalog builder uses lookup keys when available; env ID fallback.
- [x] Map lookup_key/env IDs → internal plan enum (FREE/PRO/BUSINESS) during reconciliation.
- [x] Hide tiers if a price isn’t present (only include discovered prices in catalog).

Files to touch

- `backend/app/api/routes/billing.py` (catalog builder + plan reconciliation)
- Optional: fallback to env IDs if lookup not found (temporary)

### 4) Customer + default payment methods

- [x] Always create/retrieve a Stripe Customer and persist `stripe_customer_id` for Clerk user.
- [x] For Elements flow, set `payment_settings.save_default_payment_method = on_subscription`.
- [x] Add an endpoint to update the subscription default payment method (for dunning).

Files to touch

- `backend/app/api/routes/billing.py`
- `backend/app/models/*` (ensure `stripe_customer_id` present and indexed)

### 5) Tax readiness (optional but recommended)

- [x] If enabling Stripe Tax: set `automatic_tax = { enabled: true }` on subscriptions.
- [ ] Collect billing address (or use Elements Address) as needed for tax.
  - Added DB fields & API endpoint (`POST /billing/address`) to persist + sync to Stripe; frontend Address Element still disabled.
  - Implemented behind feature flag: when `STRIPE_AUTOMATIC_TAX_ENABLED=true`, backend sends `automatic_tax: { enabled: true }` for both Checkout and Elements flows; tests cover both paths.

Files to touch

- `backend/app/api/routes/billing.py` (subscription create params)

### 6) Idempotency

- [x] Add `Idempotency-Key` to Stripe create calls (derive from user+plan+ts or a request nonce).

Files to touch

- `backend/app/api/routes/billing.py` (Checkout Session create; default_incomplete subscription create)

---

## Frontend (Next.js App Router) — required items

### 1) Subscribe page UX (Elements)

- [x] Add Express Checkout Element before Payment Element (Apple/Google Pay enabling deferred to production).
- [ ] Ensure HTTPS in dev/prod and Apple Pay domain registration before enabling (deferred to production).
- [x] Improve error states for `requires_action` (SCA) and `payment_failed` with clear retry CTA.
- [ ] Optional Address Element for tax.
- [x] Keep dark theme Appearance and force remount on theme change (already in place).

Files to touch

- `frontend/src/app/subscribe/page.tsx`

Refs

- “Add one‑click payment buttons: Embedded components”.

### 2) Plans UI

- [ ] Hide tiers with no configured price; show yearly toggle if yearly prices exist.

Files to touch

- Plans component (wherever plans are rendered) — ensure it consumes catalog with intervals

### 3) Layout polish

- [x] Add `<meta name="color-scheme" content="dark light">` to reduce flash.

Files to touch

- `frontend/src/app/layout.tsx`

---

## Customer Portal

- [ ] Configure Portal in Dashboard: product catalog, proration behavior, cancellation, PM updates, invoices.
- [ ] Ensure `return_url` and test paths: no sub, active, past_due.
- [x] API supports passing a Portal configuration ID (tested via unit test).

Files to touch

- `backend/app/api/routes/billing.py` (POST /billing/portal — can pass configuration if needed)

Refs

- “Integrate the customer portal with the API”.

---

## Security & compliance

- [ ] Never expose secret keys; only publishable key on client; load Stripe.js from `js.stripe.com`.
- [ ] Register Apple Pay domain before enabling Apple Pay.
- [x] Verify webhook signatures on raw body; enforce timestamp tolerance (anti‑replay).
- [ ] Use parameterized queries and avoid logging PII/keys. Redact sensitive fields in logs.
- [ ] Limit enabled payment methods to those you support.

---

## Observability & tests

- [ ] Sentry: add breadcrumbs/tags (user id, plan, price id, invoice id) — no PII.
- [ ] Metrics: count webhook receipts, duplicates skipped, failures, subscription state transitions.
  - Added metrics (backend): `stripe.webhook.received`, `stripe.webhook.queued`, `stripe.webhook.duplicate`, `stripe.webhook.invalid_signature`, `stripe.webhook.ignored`, `stripe.checkout.completed`, `stripe.subscription.event`, `stripe.invoice.paid`, `stripe.invoice.failed`, `stripe.invoice.action_required`.
  - Added Sentry tags on webhook/billing spans: `subscription_status`, `invoice_id`, `price_id`, plus user/plan context without PII.
- [ ] Tests (minimum):
  - [x] Webhook de-dup logic (unit tests passing).
  - [x] subscription.created/updated/deleted → plan mapping (via reconciliation + tests).
  - [ ] invoice.payment_failed/payment_action_required → state & prompts (backend logs exist; add UI + tests).
  - [x] Status reconciliation: unknown price → safe default (tests passing).

---

## Go-live checklist

- [ ] Switch to live keys and live webhook endpoint (new secret); update envs.
- [ ] Limit webhook events to what we handle; confirm 2xx rates are high.
- [ ] Register Apple Pay domain; verify on production domain over HTTPS.
- [ ] Enable Smart Retries and customer emails in Dashboard (dunning).
- [ ] Confirm proration policy and test upgrade/downgrade/cancel scenarios end‑to‑end.
- [ ] Confirm tax handling (enable Stripe Tax or intentionally disable; verify addresses).
- [ ] Run test matrix: success, SCA required, failure→retry, upgrade, downgrade, cancel, portal changes.

---

## Implementation guide (where to edit)

- Backend
  - `backend/app/api/routes/stripe_webhooks.py`: verify, de-dup, async queue, lifecycle handlers.
  - `backend/app/api/routes/billing.py`: catalog via lookup keys, Elements init params, idempotency, portal.
  - `backend/app/core/config.py`: keys & webhook secrets (multiple), Stripe settings.
  - Alembic migration: webhook events table for de-dup.
- Frontend
  - `frontend/src/app/subscribe/page.tsx`: Express Checkout, Address Element, error flows.
  - `frontend/src/app/layout.tsx`: color-scheme meta.
  - Plans component: hide missing tiers, yearly toggle.

---

## Reference docs (curated)

- Checkout/Next.js & Embedded: Stripe Checkout quickstart; Embedded form quickstart.
- Elements subscriptions (default_incomplete): Accept a payment — deferred (subscription).
- Express Checkout Element: One‑click payment buttons.
- Webhooks: Best practices; Quickstart; Signature verification & troubleshooting.
- Customer Portal: Integrate customer portal; Set up the portal.
- Subscriptions lifecycle/failures: Using webhooks with subscriptions.
- Trials/deferred: Handle subscriptions with deferred payment.

---

## Status tracker

- [x] Webhook de-dup
- [x] Async queue (Dramatiq offload)
- [x] Multiple webhook secrets
- [x] Failure & SCA handlers (backend logging + UI prompts + PM update endpoint)
- [x] Pricing via lookup keys
- [x] Idempotency on create calls
- [x] Express Checkout wiring (Apple/Google enabling deferred to prod)
- [ ] Address/Tax readiness
  - Backend persistence + sync complete; enable Address Element & add validation + test.
- [ ] Plans UI: hide tiers; yearly toggle
- [x] Color-scheme meta
- [x] Portal config verified (API supports configuration ID)
- [ ] Observability + tests (baseline in place; expand)
- [ ] Go-live checks

---

## What’s next (focused plan)

1. Frontend UX for payment recovery and SCA

- Done: Show banners/CTAs when subscription is `past_due` or `requires_action`.
- Done: Add a “Fix payment” flow using Payment Element on top of existing subscription/invoice.

1. Wallets enablement for production

- Serve over HTTPS and register Apple Pay domain; enable Google Pay per Stripe docs.

1. Payment method management

- Done: Backend endpoint to update default payment method for a subscription.
- Done: Dunning banner links to in-app recovery and Portal.

1. Pricing and plans UI

- Hide tiers with no prices; add Yearly toggle when yearly prices exist.
- Optionally extend catalog to include yearly SKUs.

1. Proration policy

- Decide and document proration for upgrades/downgrades; implement consistent behavior.
  - Proposed: Enable proration for upgrades (immediate access) and credit on downgrades at period end (no immediate refund). Configure via Stripe Dashboard (subscription proration behavior) and enforce in backend upgrade/downgrade endpoints.
  - Action: Add explicit param `proration_behavior` when modifying subscription (e.g. `create` default, `always_invoice` or `none` as needed). Tests to assert invoice line items reflect proration on upgrade.

1. Tax/address readiness

- Add Address Element; optionally enable `automatic_tax` in subscription create.

1. Observability and tests

- Add Sentry breadcrumbs/tags (user id, plan, price id, invoice id) — no PII.
- Add metrics counters for webhook events, duplicates, failures, and state transitions.
- Extend tests for failure/SCA flows and portal paths.

1. Final go-live checks

- Switch to live keys, limit webhook events, test upgrade/downgrade/cancel, and verify dunning.
