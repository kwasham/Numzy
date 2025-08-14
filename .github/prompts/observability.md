# Observability Task

## Goals

- Capture errors to Sentry on both FE/BE.
- Structured logs; no secrets/PII.

## Steps

- Frontend: wrap critical boundaries; add `instrumentation.ts` hook if missing.
- Backend: init Sentry on startup; set environment, release; capture in exception handlers and worker errors.
- Add breadcrumbs for key flows (uploads, job enqueue/dequeue).

## Output

- Code changes + checklist of signals added.
