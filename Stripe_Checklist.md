# Stripe Billing — Production Checklist (Numzy)

Purpose: a practical, production-hardening guide for our Stripe Billing integration across FastAPI backend and Next.js frontend. Use this document to track readiness and verify go-live steps.

Last updated: 2025-08-18

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

## Quick wins (do next)

- Webhook de-dup: persist processed `event.id` and early-exit on duplicates.
- Idempotency: add `Idempotency-Key` on create calls (checkout session, subscription).
- Express Checkout: add Apple Pay / Google Pay (domain registration + HTTPS).
- Pricing by lookup keys: avoid hard-coded env price IDs.

---

## Backend (FastAPI) — required items

### 1) Webhooks: security, reliability, async

- [ ] Verify signatures against the raw request body; reject if invalid.
- [ ] Return HTTP 2xx immediately; offload processing to Dramatiq.
- [ ] De-duplicate: store processed `event.id` in DB; skip repeats.
- [ ] Support secret rotation: allow multiple webhook secrets (comma-separated) and try each.
- [ ] Subscribe only to necessary events in Dashboard (reduce noise):
  - `checkout.session.*`, `customer.subscription.*`, `invoice.*`, `customer.*`

Files to touch

- `backend/app/api/routes/stripe_webhooks.py` (raw body verify, 2xx fast, enqueue, de-dup)
- `backend/app/core/config.py` (multiple secrets; env parsing)
- `backend/app/core/tasks.py` or `backend/app/app/worker.py` (Dramatiq jobs)
- Alembic migration for `stripe_webhook_events` (event_id unique, processed_at)

Notes

- See: Stripe docs “Receive Stripe events in your webhook endpoint — Best practices”.

### 2) Subscription lifecycle correctness

- [ ] On `invoice.payment_failed` → mark account “past_due” or similar; prompt to update PM.
- [ ] On `invoice.payment_action_required` → flag SCA required and guide user to complete.
- [ ] On `customer.subscription.created/updated` → set plan based on active price.
- [ ] On `customer.subscription.deleted` or status=unpaid/canceled → downgrade safely.
- [ ] Consistent proration behavior for upgrades/downgrades (document policy).

Files to touch

- `backend/app/api/routes/stripe_webhooks.py`
- `backend/app/api/routes/billing.py` (status reconciliation already in place; extend for new states)

Refs

- “Using webhooks with subscriptions — Handle payment failures & requires_action”.

### 3) Pricing/catalog via lookup keys

- [ ] Replace env price IDs with Stripe Price `lookup_key`s like:
  - `plan:free:monthly`, `plan:pro:monthly`, `plan:team:monthly`, `plan:pro:yearly`, `plan:team:yearly`
- [ ] Map lookup_key → internal plan enum (FREE/PRO/TEAM) and interval.
- [ ] Hide tiers if a price isn’t present.

Files to touch

- `backend/app/api/routes/billing.py` (catalog builder + plan reconciliation)
- Optional: fallback to env IDs if lookup not found (temporary)

### 4) Customer + default payment methods

- [ ] Always create/retrieve a Stripe Customer and persist `stripe_customer_id` for Clerk user.
- [ ] For Elements flow, set `payment_settings.save_default_payment_method = on_subscription`.
- [ ] Add an endpoint to update the subscription default payment method (for dunning).

Files to touch

- `backend/app/api/routes/billing.py`
- `backend/app/models/*` (ensure `stripe_customer_id` present and indexed)

### 5) Tax readiness (optional but recommended)

- [ ] If enabling Stripe Tax: set `automatic_tax = { enabled: true }` on subscriptions.
- [ ] Collect billing address (or use Elements Address) as needed for tax.

Files to touch

- `backend/app/api/routes/billing.py` (subscription create params)

### 6) Idempotency

- [ ] Add `Idempotency-Key` to Stripe create calls (derive from user+plan+ts or a request nonce).

Files to touch

- `backend/app/api/routes/billing.py` (Checkout Session create; default_incomplete subscription create)

---

## Frontend (Next.js App Router) — required items

### 1) Subscribe page UX (Elements)

- [ ] Add Express Checkout Element (Apple Pay/Google Pay/Link) before Payment Element.
- [ ] Ensure HTTPS in dev/prod and Apple Pay domain registration before enabling.
- [ ] Improve error states for `requires_action` (SCA) and `payment_failed` with clear retry CTA.
- [ ] Optional Address Element for tax.
- [ ] Keep dark theme Appearance and force remount on theme change (already in place).

Files to touch

- `frontend/src/app/subscribe/page.tsx`

Refs

- “Add one‑click payment buttons: Embedded components”.

### 2) Plans UI

- [ ] Hide tiers with no configured price; show yearly toggle if yearly prices exist.

Files to touch

- Plans component (wherever plans are rendered) — ensure it consumes catalog with intervals

### 3) Layout polish

- [ ] Add `<meta name="color-scheme" content="dark light">` to reduce flash.

Files to touch

- `frontend/src/app/layout.tsx`

---

## Customer Portal

- [ ] Configure Portal in Dashboard: product catalog, proration behavior, cancellation, PM updates, invoices.
- [ ] Ensure `return_url` and test paths: no sub, active, past_due.
- [ ] Optionally create multiple Portal configurations for different cohorts (via API).

Files to touch

- `backend/app/api/routes/billing.py` (POST /billing/portal — can pass configuration if needed)

Refs

- “Integrate the customer portal with the API”.

---

## Security & compliance

- [ ] Never expose secret keys; only publishable key on client; load Stripe.js from `js.stripe.com`.
- [ ] Register Apple Pay domain before enabling Apple Pay.
- [ ] Verify webhook signatures on raw body; enforce timestamp tolerance (anti‑replay).
- [ ] Use parameterized queries and avoid logging PII/keys. Redact sensitive fields in logs.
- [ ] Limit enabled payment methods to those you support.

---

## Observability & tests

- [ ] Sentry: add breadcrumbs/tags (user id, plan, price id, invoice id) — no PII.
- [ ] Metrics: count webhook receipts, duplicates skipped, failures, subscription state transitions.
- [ ] Tests (minimum):
  - Webhook de-dup logic.
  - subscription.created/updated/deleted → plan mapping.
  - invoice.payment_failed/payment_action_required → state & prompts.
  - Status reconciliation: unknown price → safe default.

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

- [ ] Webhook de-dup + async
- [ ] Multiple webhook secrets
- [ ] Failure & SCA handlers
- [ ] Pricing via lookup keys
- [ ] Idempotency on create calls
- [ ] Express Checkout (Apple/Google/Link)
- [ ] Address/Tax readiness
- [ ] Plans UI: hide tiers; yearly toggle
- [ ] Color-scheme meta
- [ ] Portal config verified
- [ ] Observability + tests
- [ ] Go-live checks
