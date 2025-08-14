# Numzy

Fresh repository baseline after reset (2025-08-13).

## What is here

- Backend: FastAPI + SQLAlchemy async + Dramatiq worker (`backend/`)
- Frontend: Next.js App Router (clean scaffold in `frontend/app`), legacy exploratory code in `frontend/src` (migrate or delete later)
- Shared types in `shared/`
- Docker Compose for local infra (Postgres optional, Redis, MinIO, API, worker, MCP prompt server)

## Quick Start

```bash
# Backend services (infra + app profiles)
./scripts/run-be-fe.sh --rebuild

# Or manually
docker compose --profile infra --profile app --profile local-db up -d

# Frontend (in another terminal)
cd frontend
pnpm install
pnpm dev
```

API: <http://localhost:8000/docs>  
Frontend: <http://localhost:3000>

## Environment

See `frontend/.env.example` and root `.env` for required variables. Key groups: Auth, Clerk, Supabase, Sentry.

## Sentry

Minimal instrumentation lives in `frontend/instrumentation.ts` and backend initialization in `backend/app/api/main.py` if DSN provided.

## Next Steps

- Migrate needed pages from `frontend/src/app` into `frontend/app` then remove `src/app`.
- Implement receipt amount filtering in backend `/receipts` endpoint.
- Re-enable Sentry release + source map upload in CI when ready.
- Add tests: run `pytest` for backend; `pnpm test` in frontend.

## Conventions

- Use feature branches: `feat/<topic>`
- Commit style: `type(scope): message`
- Keep Server Components pure; use client boundaries for interactive pieces.

## License

Proprietary (update if you decide to open source later).
