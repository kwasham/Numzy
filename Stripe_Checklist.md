# Stripe Billing — Production Checklist (Numzy)

Purpose: a practical, production-hardening guide for our Stripe Billing integration across FastAPI backend and Next.js frontend. Use this document to track readiness and verify go-live steps.

Last updated: 2025-08-23 (added SCA & dunning funnel metrics + recovery instrumentation)

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

- [x] On `invoice.payment_failed` → mark account `past_due`; backend sets `payment_state=past_due`; UI banner & test present.
- [x] On `invoice.payment_action_required` → mark `requires_action`; backend sets state; UI banner & test present.
- [x] On `customer.subscription.created/updated` → set plan based on active price.
- [x] On `customer.subscription.deleted` or status=unpaid/canceled → downgrade safely.
- [x] Yearly interval support in plan change endpoint (interval switching implemented).
- [x] Subscription change preview endpoint (delta + upgrade/downgrade classification).
- [x] Deferred downgrade scheduling (sets `cancel_at_period_end` + `metadata.pending_plan`).
- [x] Reconciliation worker applies scheduled downgrade before period end (Dramatiq actor `reconcile_pending_subscription_downgrades`; needs prod scheduling & monitoring).
- [ ] Consistent proration policy documentation & enforcement (core doc & upgrade/downgrade tests DONE; interval switch nuance + invoice line item validation PENDING).

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

- [x] Yearly toggle (auto-shown when yearly pricing detected).
- [x] Plan change preview (upgrade/downgrade delta) + deferred downgrade scheduling UI.
- [x] Hide tiers with no configured price (catalog filtering now in place).
- [x] Visual indicator when a downgrade is scheduled (badge + header text using `pending_plan`).

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

- [ ] Sentry: add breadcrumbs/tags (user id, plan, price id, invoice id) — no PII (PARTIAL: subscription, preview, change, dunning/SCA recovery breadcrumbs in place; reconciliation batch start/end summary still TODO).
- [ ] Metrics: coverage for webhook intake, subscription lifecycle, changes, dunning/SCA funnel, reconciliation.
  - Present: `stripe.webhook.received`, `stripe.webhook.queued`, `stripe.webhook.duplicate`, `stripe.webhook.invalid_signature`, `stripe.webhook.ignored`, `stripe.checkout.completed`, `stripe.subscription.event`, `stripe.subscription.plan.changed`, `stripe.subscription.preview`, `stripe.subscription.change`, `stripe.subscription.change.error`, `stripe.subscription.downgrade_scheduled`, `stripe.subscription.downgrade.applied`, `stripe.subscription.reconcile.run`, `stripe.invoice.paid`, `stripe.invoice.failed`, `stripe.invoice.action_required`, `stripe.dunning.entered`, `stripe.dunning.recovered`, `stripe.sca.entered`, `stripe.sca.completed`.
  - Remaining nice-to-have: dunning recovery duration metric (time-to-recover), subscription reconcile error rate alert thresholds, proration invoice line delta metrics.
- [ ] Tests (minimum & progress):
  - [x] Webhook de-dup logic.
  - [x] subscription.created/updated/deleted → plan mapping.
  - [x] invoice.payment_failed/payment_action_required → UI banners (frontend tests) & backend state update.
  - [x] Status reconciliation unknown price fallback.
  - [x] Subscription preview endpoint (upgrade & downgrade + no‑op) (NOTE: confirm no-op test added else add).
  - [x] Deferred downgrade scheduling sets metadata + cancel_at_period_end.
  - [x] Reconciliation worker fulfillment test (applies pending downgrade & clears metadata).
  - [ ] Proration policy deep assertions (interval switch nuance; invoice line item verification).

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
- [x] Failure & SCA handlers (backend logging + initial UI prompts; richer UX pending)
- [x] Pricing via lookup keys
- [x] Idempotency on create calls
- [x] Express Checkout wiring (Apple/Google enabling deferred to prod)
- [ ] Address/Tax readiness
  - Backend persistence + sync complete; enable Address Element & add validation + test.
- [x] Plans UI: yearly toggle + preview + schedule downgrade
- [x] Plans UI: hide tiers with missing prices
- [x] Plans UI: pending downgrade indicator
- [x] Color-scheme meta
- [x] Portal config verified (API supports configuration ID)
- [ ] Observability + tests (baseline in place; expand)
  - Added: reconciliation run metrics (`stripe.subscription.reconcile.run`), change error metric, plan change granular tag, SCA/past_due banner tests.
    - Remaining: proration policy tests, address element test, live key matrix, webhook pruning execution, wallet enablement.
    - Scheduling: in-process cron loop enabled via `RECONCILE_CRON_ENABLED=true` (worker) with interval envs documented below.
- [ ] Go-live checks
- [x] Yearly interval support in backend change endpoint
- [x] Subscription preview endpoint
- [x] Deferred downgrade scheduling (metadata + cancel_at_period_end)
- [x] Pending-plan reconciliation automation (worker actor present; scheduling & monitoring TODO)

---

## What’s next (focused plan)

1. Schedule & monitor reconciliation (DONE initial)

- Implemented lightweight in-process cron (env `RECONCILE_CRON_ENABLED=true`); configurable via:
  - `RECONCILE_CRON_INTERVAL_SECONDS` (default 420)
  - `RECONCILE_CRON_LOOKAHEAD_SECONDS` (default 900)
  - `RECONCILE_CRON_BATCH_LIMIT` (default 200)
- Next: add alerting wiring (outside codebase) for high applied/error counts.

1. Proration policy docs & tests (PARTIAL)

- Added `docs/billing-proration-policy.md` documenting upgrade vs deferred downgrade vs no-op.
- Tests updated to assert proration_behavior for upgrade and none for deferred downgrade.
- Remaining: interval switch nuance (monthly->yearly) & explicit invoice line item inspection (future enhancement).

1. Reconciliation fulfillment test (DONE)

- Implemented backend test `test_reconciliation_applies_and_clears_metadata` asserting downgrade application clears metadata & unsets cancel.

1. Failure / SCA UX automation (DONE)

- Added frontend `dunning-banner.test.tsx` covering requires_action and past_due banners + onFix handler.

1. Address & Tax UI

- Integrate Address Element (behind flag); persist & sync; add e2e test when tax flag enabled.

1. Wallet enablement

- Register Apple Pay domain (prod HTTPS); enable Apple & Google Pay; conditionally render one‑click buttons.

1. Webhook pruning execution

- Run `scripts/stripe_prune_webhook.py --apply`; store snapshot of final event allowlist in repo.

1. Additional observability (partial)

- Completed: reconciliation run metrics/breadcrumbs; change error metric; granular from->to tag.
- TODO: SCA funnel metrics (attempt/completed), dunning recovery timing, alert thresholds config.

1. Go-live checklist finalization

- Live keys, portal matrix (new sub, upgrade, downgrade, cancel, past_due, requires_action), rollback/runbook doc.

1. Performance & dunning simulation (optional but valuable)

- Script to simulate invoice failures & recovery to validate alerts + metrics.

Completed since last revision: Added SCA & dunning funnel metrics (`stripe.sca.entered/completed`, `stripe.dunning.entered/recovered`), recovery state updates, refactored webhook handler, expanded metrics list; prior additions (reconcile.run, plan.changed, change.error, fulfillment test, banners) retained.

Readiness summary:

Must-have DONE:

- Verified webhooks (multi-secret, de-dup, async queue).
- Subscription change + preview + deferred downgrade + reconciliation (scheduled via cron envs).
- Plan mapping & lifecycle (upgrade/downgrade, cancellation, unpaid handling).
- Dunning & SCA state persistence + frontend banners + funnel metrics (entered/completed / recovered).
- Observability baseline (comprehensive metric set; key breadcrumbs).

Remaining BEFORE production (blocking):

1. Execute webhook pruning in live Dashboard; capture allowlist snapshot.
2. Final proration policy nuances (interval switch) + add invoice line validation test (or explicitly defer & document).
3. Address Element enablement + test (or explicit decision to defer tax readiness).
4. Wallet (Apple Pay domain verification + Google Pay) enablement or document deferment.
5. Go-live runbook execution: live keys, portal matrix QA, rollback rehearsal.

Strongly Recommended (non-blocking but valuable):

- Alerting thresholds (change.error rate, reconcile anomalies, invoice failure %, recovery lag).
- Dunning recovery duration metric.
- No-op preview explicit test if missing.

Conclusion: Integration is feature-complete for core subscription management and resilient to common failure/SCA paths. Proceed to operational hardening (pruning, tax/wallet decisions, proration nuance test, alerts) before flipping live keys.
