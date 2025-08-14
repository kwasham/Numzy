# Numzy Project Gap Analysis (2025-08-13)

This report compares the current repository state to `backend/Master_Checklist.md` and highlights discrepancies, missing features, and recommended next actions.

## Legend

- ✅ Present & aligned
- ⚠️ Partial / needs enhancement
- ❌ Missing
- 💤 Deferred / not started but lower priority

## 1. Backend

| Area | Checklist Claim | Current State Evidence | Status | Notes |
|------|-----------------|------------------------|--------|-------|
| FastAPI app + modular routers | Completed | `app/api/routes/*.py` present (receipts, audit_rules, prompts, evaluations, cost_analysis, users, teams, jobs, events) | ✅ | Structure intact. |
| Alembic migrations | Completed | `backend/alembic/` and `migrations/versions` exist | ✅ | Multiple migration scripts. |
| Receipt endpoints incl. reprocess & batch | Completed | `receipts.py` has upload, batch, reprocess, download URL, audit | ✅ | Works; list currently no filtering/pagination. |
| Dashboard endpoints | (Implicit) | `dashboard.py` exists but empty | ❌ | File placeholder only; implement KPIs/usage. |
| Sentry backend init | Partial | Init done in `app/api/main.py` if DSN set | ⚠️ | CI release + env unconfigured. |
| Rule engine basic | Completed | `rule_engine.py` and usage in `audit_service.py` | ✅ | Deterministic rules working. |
| LLM / MCP integration | In progress | LLM hooks guarded; MCP not integrated | ⚠️ | Add wiring & graceful feature flags. |
| Billing foundation | Completed | `billing_service.py` exists | ⚠️ | Need Stripe integration & metering endpoints. |
| Storage (MinIO) | Completed | `storage_service.py` with save & path resolution | ✅ | Appears operational. |
| Background tasks (Dramatiq) | Completed | `app/core/tasks.py`, worker script present | ✅ | Not inspected log configs here; assume operational. |
| Task status / retry tracking | Completed | Fields in `Receipt` (status, task_id, progress, retry) | ✅ | Implemented. |
| Security: auth (Clerk) | Claimed done | `dependencies.get_clerk_user` (not inspected here) | ⚠️ | Need to verify enforcement across all routers & RBAC. |
| Rate limiting | Partial | `enforce_rate_limit`, `enforce_tiered_rate_limit` referenced | ⚠️ | Confirm implementation & persistence (not shown). |

### Backend Gaps / Actions

1. Implement `dashboard.py` endpoints (KPIs, recent receipts, usage summary).  
2. Add list filtering to `/receipts` (date range, status, amount min/max, search).  
3. Stripe integration scaffold (pricing models, subscription check decorator).  
4. Add Sentry release env var usage; unify `SENTRY_RELEASE`.  
5. Expose webhook receiver for processing completion (result webhooks).  
6. Implement DLQ / priority queue (Dramatiq: separate queues + retries to DLQ).  
7. Confirm & test rate limiting logic; add tests.  

## 2. Frontend

| Area | Checklist Claim | Current State Evidence | Status | Notes |
|------|-----------------|------------------------|--------|-------|
| App Router structure | Claimed set up | `src/app/` present | ✅ | Active root. |
| Tailwind v4 + Shadcn + Tremor | Claimed configured | Not visible in current file listing (Tailwind config missing) | ❌ | Likely lost in reset. |
| TanStack Query | Claimed done | No `@tanstack/react-query` imports found (not searched fully) | ❌ | Re-add provider & hooks. |
| Receipt upload UI | Done | `receipt-upload-widget.js` | ✅ | Functionality appears present. |
| Batch uploads | Done | Widget includes multi-file logic? (Need inspection) | ⚠️ | Verify parallel progress UI. |
| Detail modal with extraction/audit | Done | Not yet inspected; presumed lost if component missing | ⚠️ | Search components to confirm. |
| Receipt search & history | Not done | No filtering in backend list | ❌ | Requires API + UI. |
| Analytics dashboard | Not done | No charts components referenced | ❌ | Rebuild with Tremor or alternative. |
| Rule builder UI | Not done | No component | ❌ | Pending concept. |
| Dark mode | Not done | Theme provider exists but verify color modes | ⚠️ | Add toggle if missing. |
| Glassmorphism design | Not done | Not evident in CSS | ❌ | Reimplement if desired. |
| Error boundaries | Planned | `global-error.tsx` exists in `src/app/errors`? (Need confirm) | ⚠️ | Add top-level + per critical route. |
| Sentry front init | Partial | `src/app/instrumentation.ts` present | ⚠️ | Release, source maps missing. |

### Frontend Gaps / Actions

1. Reintroduce Tailwind / Shadcn / Tremor stack or update checklist to reflect new design direction.  
2. Add React Query provider at root (caching receipt list & mutations).  
3. Rebuild receipt detail modal & real-time progress using polling or SSE/websocket if available.  
4. Implement search & filters (status, date range, merchant text, amount).  
5. Add analytics (spend by timeframe, category) once backend KPIs ready.  
6. Add error boundary at `src/app/global-error.tsx` if missing; user-friendly fallback.  
7. Implement dark mode toggle & persist preference.  
8. Clean design system decision (CSS Modules vs Tailwind vs MUI). Update checklist accordingly.  

## 3. Observability & Ops

| Item | Status | Notes |
|------|--------|-------|
| Sentry DSN conditional init | ✅ | Works; safe no-op. |
| Release tagging across services | ❌ | No unified release variable across backend & worker yet. |
| Source map upload | ❌ | No build wrapper / CI step. |
| Performance tracing sampling strategy | ❌ | Defaults only, not environment-tuned. |
| Alert rules & PII scrubbing | ❌ | Not configured. |
| OpenTelemetry | ❌ | Not present. |
| Structured logging | ⚠️ | Standard logging enabled; add JSON formatter + correlation IDs. |

## 4. Missing / Orphaned Files

- `backend/app/api/routes/dashboard.py` empty placeholder.  
- Any lost frontend stack (Tailwind config, component library) should either be restored or checklist updated to reflect a pivot (e.g., pure MUI approach).  

## 5. Suggested Priority (Next 10 Days)

Day 1-2: Backend list filtering + dashboard KPIs; unify Sentry init & release var.
Day 3: Frontend Query provider + receipts list with filters (status/date/amount/search).
Day 4: Receipt detail modal & reprocess + live progress (polling each 2s).
Day 5: Basic analytics (total receipts, processed %, avg processing time) using new `/dashboard` endpoints.
Day 6: Stripe integration scaffold (plans, webhooks stub) OR finalize search UX if billing deferred.
Day 7: Sentry release + source maps CI job; basic alert rule doc.
Day 8: Dark mode + design pass (choose Tailwind vs MUI focus).
Day 9: Rule builder initial data model + placeholder UI.
Day 10: Webhook callback implementation + worker DLQ strategy.

## 6. Quick Wins (High Impact, Low Effort)

- Implement amount/date/status filters in `/receipts` query (single query refactor).
- Fill `dashboard.py` with KPI aggregation (COUNTs & AVG durations).
- Add single React Query provider; migrate receipt calls to hooks.
- Add global error boundary with user-friendly message & Sentry capture.
- Introduce a `RELEASE` env var and propagate to Sentry init (backend + frontend).

## 7. Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Divergence between checklist & reality | Misaligned planning | Keep this report updated; adjust checklist headings. |
| Missing analytics endpoints slows UI | UI blockers | Implement minimal KPIs early. |
| Lack of source maps | Harder prod debugging | Add Sentry upload in CI before feature expansion. |
| Unverified rate limiting | Abuse or perf issues | Add tests & logging; confirm algorithm. |
| Design system indecision | Rework later | Decide on MUI-only vs Tailwind hybrid this week. |

## 8. Open Questions

1. Continue with MUI only or restore Tailwind + Shadcn stack?  
2. Is Clerk still the active auth provider in production?  
3. Is real-time update via polling sufficient, or migrate to SSE/websocket?  
4. Billing timeline: MVP gating or post-MVP?  

## 9. Action Register

| ID | Action | Owner | Target Date |
|----|--------|-------|-------------|
| A1 | Implement `/dashboard/kpis` endpoint |  | +2 days |
| A2 | Add receipt filters (date/status/amount/search) |  | +2 days |
| A3 | Add React Query provider & hooks |  | +3 days |
| A4 | Configure Sentry release + source maps |  | +7 days |
| A5 | Decide on design system approach |  | +5 days |
| A6 | Stripe integration scaffold |  | +8 days |
| A7 | Implement result webhook endpoint |  | +9 days |

---
Generated automatically. Update `Master_Checklist.md` or this file as tasks are completed.
