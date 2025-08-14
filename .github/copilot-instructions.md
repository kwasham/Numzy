# Numzy — Copilot Instructions (repo-wide)

## Objective
Help me ship production-quality features across a pnpm monorepo:
- **Frontend:** Next.js App Router (prefer Server Components; use Client boundaries only for interactivity).
- **Backend:** FastAPI (async), SQLAlchemy async, Pydantic v2 (if present), S3-compatible storage via MinIO, Redis broker.
- **Workers:** Dramatiq for background jobs (no Celery). 
- **Infra:** Docker Compose profiles; local dev via `pnpm` workspaces.
- **Observability:** Sentry; never log secrets/PII.

## Agentic behavior
<context_gathering>
Goal: gather just-enough context, then act.
Steps:
1) Open touched files + referenced symbols; scan related tests/types.
2) Stop when you can name exact files/symbols to edit (avoid over-search).
Proceed to make the edit with minimal diff.
</context_gathering>

<persistence>
- Don’t bounce back with questions if you can proceed safely.
- If a constraint is ambiguous, choose the safest reasonable path and note assumptions at the end.
</persistence>

<tool_preamble>
Before edits: Restate the task in one sentence and list concrete steps.
After edits: Summarize what changed, why, and follow-ups (if any).
</tool_preamble>

## Conventions
- Branches: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`.
- Commits: `type(scope): message`.
- Frontend: Keep Server Components pure; colocate server actions; prefer TypeScript when file is TS, otherwise match existing file type.
- Backend: async all the way; dependency-inject DB sessions; return Pydantic models; never block for long work—offload to Dramatiq.
- Storage: use S3/MinIO client; stream uploads; set content-type; avoid reading large files fully in memory.
- Auth: Clerk; never leak tokens; check server/client boundary before accessing `process.env`.
- Error handling: raise typed HTTPExceptions; map worker failures to safe user messages.
- Tests: add/extend tests for new behavior (prefer smallest viable coverage).

## Security & Secrets
- No secrets in logs; redact PII; use parameterized SQL only; validate external input (Zod/Pydantic).
- For uploads: validate MIME/size; generate time-limited signed URLs.

## Verbosity & Output
- Chat replies concise; diffs minimal.
- When risk is high (migrations, auth, infra), include rationale and rollback steps.

## How to use in VS Code Copilot Chat
- Use participants and context vars:
  - `@workspace` + `#file`, `#folder`, `#codebase`, `#changes` to ground responses in repo files.
- When you see `prompts/*.md`, ingest it as spec and follow it.
