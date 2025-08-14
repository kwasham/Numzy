# Numzy Monorepo

## Overview

Numzy is a full‑stack receipt intelligence platform built as a pnpm monorepo:

- **Frontend:** Next.js App Router (Server Components first) + MUI v7.
- **Backend API:** FastAPI (async) + SQLAlchemy (async) + Pydantic.
- **Workers:** Dramatiq for background & long‑running extraction / evaluation jobs.
- **Storage:** S3‑compatible (MinIO locally) for original & processed artifacts.
- **Messaging/Cache:** Redis (Dramatiq broker + caching).
- **Observability:** Sentry (API, workers, frontend) with PII scrubbing & spans.

The repo also ships a prompt‑driven developer workflow (see `prompts/` and `.github/copilot-instructions.md`) to keep AI assistance aligned with engineering standards.

## Key Features

- Streamed, validated file uploads → background extraction → structured data.
- Idempotent Dramatiq jobs with retry/backoff & Sentry span instrumentation.
- Secure storage: sanitized object keys, MIME & size validation, signed URLs.
- Centralized Sentry init (`backend/app/core/observability.py`) + task spans.
- Frontend error boundaries & (planned) performance instrumentation.

## Tech Stack

| Area | Technologies |
|------|--------------|
| Frontend | Next.js (App Router), React, TypeScript, MUI v7 |
| Backend API | FastAPI (async), SQLAlchemy async, Pydantic |
| Workers | Dramatiq (Redis broker) |
| Storage | MinIO (S3 API), Local filesystem for dev artifacts |
| Observability | Sentry (API, worker, frontend) |
| Auth (planned) | Clerk |
| Package Mgmt | pnpm workspaces + Python `requirements.txt` |

## Repository Structure

```text
backend/            FastAPI app, Dramatiq worker, models, services
frontend/           Next.js App Router application
shared/             Shared TypeScript types
prompts/            Modular task & rubric prompt specs
.github/            Copilot / workflow instructions
scripts/            Dev / generation scripts
migrations/         Alembic migration environment
storage/, uploads/  Local artifact & upload storage (dev only)
```

## Backend Flow (Text Diagram)

```text
Client Upload -> FastAPI Endpoint -> Validate + Persist metadata ->
Dramatiq enqueue (extraction) -> Worker spans tasks:
fetch -> parse/extract -> evaluate -> audit -> finalize
Results -> DB + S3/MinIO -> API retrieval -> Frontend display
```

## Frontend Guidelines

- Prefer Server Components; mark interactive ones with `"use client"`.
- Keep server actions in component files or sibling `actions.ts`.
- Provide accessible components (ARIA roles/labels, keyboard focus states).
- Temporary note: current routes still live under `frontend/src/app/` (legacy template). A minimal `src/app/page.js` now redirects `/` to `/dashboard`. Gradually migrate required routes into the top-level `app/` (remove `src/app` afterwards).

## Observability

- Unified init in `backend/app/core/observability.py` sets DSN, environment, release (TODO CI injection) & scrubs PII via `_before_send`.
- Dramatiq tasks wrap major phases in Sentry spans (extraction, evaluation, audit, finalize).
- Frontend error boundaries report to Sentry with user‑friendly UI.
- Upcoming: dynamic `release` tagging, source map upload, performance transactions.

## Prompt‑Driven Workflow

Use curated specs in `prompts/` for consistent AI‑assisted changes:

- `fastapi-endpoint.md` – add/modify API routes
- `dramatiq-job.md` – create safe idempotent workers
- `storage-minio.md` – presigned upload & retrieval flows
- `observability.md` – instrumentation & logging
- `next-page.md` – App Router page/route patterns
- `mui-component.md` – reusable accessible MUI components
- `tests.md` – testing playbook
- `review.md` – rubric for PR evaluation

Global behavioral rules live in `.github/copilot-instructions.md`. In Copilot Chat reference them with `@workspace` + `#folder`/`#file` context markers.

## Quick Start

```bash
# Install JS deps
yarn global add pnpm # if pnpm not installed
pnpm install

# (Optional) Python venv
printf "Creating venv..." && python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Start full stack (backend infra, API, worker, optional frontend)
./scripts/start-dev.sh --env-stub

# (Alt) Start only backend (then run pnpm dev separately)
./scripts/start-dev.sh --no-frontend

# (Alt) Run API locally (if not via compose)
uvicorn backend.app.api.main:app --reload
```

API Docs: <http://localhost:8000/docs>  
Frontend: <http://localhost:3000>

## Environment Variables (Sample)

Backend:

- `DATABASE_URL` (e.g. `sqlite+aiosqlite:///./app.db` for dev)
- `SENTRY_DSN`
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_SECURE`
- `REDIS_URL`
- `CLERK_SECRET_KEY` (future auth)

Frontend:

- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_SENTRY_DSN`
- Clerk public keys (when integrated)

Provide `.env.example` in a follow‑up (TODO).

## Database & Migrations

- Alembic config under `migrations/`.
- Create migration: `alembic revision --autogenerate -m "<message>"`.
- Apply: `alembic upgrade head`.

## Background Jobs

- Dramatiq actors in `backend/app/core/tasks.py`.
- Enqueue from API; never block request path on heavy work.
- Ensure idempotency (check existing DB state / object key collisions).

## Testing

Backend:

- Pytest (`backend/pytest.ini`).
- Async tests: routes, models, Dramatiq flows (use test Redis & MinIO buckets).

Frontend:

- (Add Vitest/Jest) – follow `prompts/tests.md`: render, props, a11y, edge cases.

Planned CI: run both suites + lint + Sentry release tagging.

## Security & Data Handling

- No secrets/PII in logs (scrubber enforced via Sentry before_send hook).
- Validate all external inputs (Pydantic / Zod) pre‑persistence.
- Stream large uploads; avoid full in‑memory buffering.

## Conventions

- Branches: `feat/<topic>`, `fix/<topic>`, `chore/<task>`.
- Commit style: `type(scope): message`.
- Keep diffs minimal; avoid drive‑by refactors.

## Roadmap (Short)

- Auth integration (Clerk) + role‑based permissions.
- Dynamic Sentry release + source map upload.
- Performance metrics dashboards.
- Enhanced evaluation scoring pipeline.
- CI pipeline (tests, migrations smoke, release tagging).

## License

TBD (add license file / notice).

## Quick Prompt Reference

| Task | Spec |
|------|------|
| Add API endpoint | `prompts/fastapi-endpoint.md` |
| New worker job | `prompts/dramatiq-job.md` |
| Storage flow | `prompts/storage-minio.md` |
| Observability | `prompts/observability.md` |
| Next.js page | `prompts/next-page.md` |
| UI Component | `prompts/mui-component.md` |
| Tests | `prompts/tests.md` |
| Review | `prompts/review.md` |

---
Extend this README with diagrams (ERD, sequence) or env templates as they mature; keep sections concise & action‑oriented.
