# Numzy — Copilot Pack (All-in-One)

This single file combines:

1. **Repo-wide Copilot rules** (always-on behavior)
2. **Task-specific prompt specs** (FastAPI endpoints, Dramatiq jobs, Next.js pages, MUI components, tests, observability, storage/MinIO)
3. **Usage examples** for VS Code Copilot Chat

> Keep as one file or split back into:
>
> - `.github/copilot-instructions.md`
> - `prompts/*.md`
> - `prompts/example.md`

---

## Table of Contents

1. [Repo-wide Copilot Instructions](#1-repo-wide-copilot-instructions-equivalent-to-githubcopilot-instructionsmd)
1. [Prompt Specs](#2-prompt-specs-equivalent-to-promptsmd)

- [Review Rubric](#promptsreviewmd--review-rubric-numzy)
  - [FastAPI Endpoint](#promptsfastapi-endpointmd--implementmodify-a-fastapi-endpoint)
  - [Dramatiq Job](#promptsdramatiq-jobmd--addmodify-a-dramatiq-job)
  - [Next.js Page/Route](#promptsnext-pagemd--nextjs-app-router-pageroute)
  - [MUI Component](#promptsmui-componentmd--mui-v6-component-spec)
  - [Testing Playbook](#promptstestsmd--testing-playbook)
  - [Observability](#promptsobservabilitymd--sentry--logging)
  - [Storage / MinIO](#promptsstorage-miniomd--s3minio-upload--retrieval)

1. [Examples (Usage)](#3-examples-how-to-use-with-vs-code-copilot-chat)
1. [Troubleshooting & Patterns](#4-troubleshooting--patterns)

---

## 1) Repo-wide Copilot Instructions (equivalent to `.github/copilot-instructions.md`)

### Numzy — Copilot Instructions (repo-wide)

### Objective

Help me ship production-quality features across a pnpm monorepo:

- **Frontend:** Next.js App Router (prefer Server Components; use Client boundaries only for interactivity).
- **Backend:** FastAPI (async), SQLAlchemy async, Pydantic v2 (if present), S3-compatible storage via MinIO, Redis broker.
- **Workers:** Dramatiq for background jobs (no Celery).
- **Infra:** Docker Compose profiles; local dev via `pnpm` workspaces.
- **Observability:** Sentry; never log secrets/PII.

### Agentic behavior

```text
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
```

### Conventions

- Branches: `feat/<topic>`, `fix/<topic>`, `chore/<topic>`.
- Commits: `type(scope): message`.
- Frontend: Keep Server Components pure; colocate server actions; prefer TypeScript when file is TS, otherwise match existing file type.
- Backend: async all the way; dependency-inject DB sessions; return Pydantic models; never block for long work—offload to Dramatiq.
- Storage: use S3/MinIO client; stream uploads; set content-type; avoid reading large files fully in memory.
- Auth: Clerk; never leak tokens; check server/client boundary before accessing env vars.
- Error handling: raise typed HTTPExceptions; map worker failures to safe user messages.
- Tests: add/extend tests for new behavior (prefer smallest viable coverage).

### Security & Secrets

- No secrets in logs; redact PII; use parameterized SQL only; validate external input (Zod/Pydantic).
- For uploads: validate MIME/size; generate time-limited signed URLs.

### Verbosity & Output

- Chat replies concise; diffs minimal.
- When risk is high (migrations, auth, infra), include rationale and rollback steps.

### How to use in VS Code Copilot Chat

- Use participants and context vars:
  - `@workspace` + `#file`, `#folder`, `#codebase`, `#changes` to ground responses in repo files.
- When you see `prompts/*.md`, ingest it as spec and follow it.

---

## 2) Prompt Specs (equivalent to prompts/*.md)

### prompts/review.md — Review Rubric (Numzy)

```markdown
# Review Rubric (Numzy)
Output: summary + checklist with pass/fail + concrete follow-ups.

## Scope
- Change matches linked issue/goal; no drive-by refactors.

## Backend
- Async FastAPI routes; SQLAlchemy sessions managed correctly; no blocking work in request path (use Dramatiq actor).
- DTOs/validators present; HTTP status codes correct; errors typed.

## Frontend
- App Router: server vs client boundary respected; no secrets client-side.
- Components typed; accessibility (roles, labels, keyboard) checked.

## Storage & Background
- S3/MinIO usage streams data; content-type set; keys sanitized.
- Dramatiq tasks idempotent; retries/backoff configured; result paths observable.

## Observability & Security
- Sentry capture on error paths; PII redaction in logs.
- Inputs validated; SQL/ORM safe; secrets never logged.

## Tests & Docs
- Unit/integration tests for new behavior.
- Readme or JSDoc updated if public API changed.
```

### prompts/fastapi-endpoint.md — Implement/modify a FastAPI endpoint

```markdown
# Task: Implement/modify a FastAPI endpoint

## Inputs
- Endpoint path & method
- Request/response models (Pydantic v2 if present)
- DB access via async SQLAlchemy
- Long-running work -> Dramatiq actor

## Steps
1) Define/extend Pydantic models (validate, docstrings).
2) Implement route function (async), inject session, handle errors.
3) If heavy work: enqueue Dramatiq task; return 202 + task id.
4) Cover with tests: happy path + edge cases + auth errors.

## Output format
- Minimal unified diff for changed files.
- Short rationale + assumptions + follow-ups.

## Notes
- Use dependency-injected DB session.
- Prefer `SELECT ... LIMIT ...` for pagination.
- Never block on I/O; stream uploads; sanity-check MIME/size.
```

### prompts/dramatiq-job.md — Add/modify a Dramatiq job

```markdown
# Task: Add/modify a Dramatiq job

## Requirements
- Idempotent job function (@dramatiq.actor), small input payloads.
- Retries/backoff; error logging to Sentry.
- Store results/side effects in DB or object storage, not in memory.

## Steps
1) Define typed payload schema.
2) Implement actor with try/except; raise for retryable errors.
3) Add enqueue helper from API layer; return a job id.
4) Add tests: success, retry, poison message handling.

## Output
- Diff + brief rationale.
```

### prompts/next-page.md — Next.js App Router page/route

```markdown
# Task: Create/modify a Next.js App Router page/route

## Constraints
- Prefer Server Components; mark client components with "use client".
- Keep server actions in the same file or a sibling actions.ts.
- Use TypeScript when the existing file is TS.
- Respect existing design tokens; integrate with Sentry if needed.

## Steps
1) Outline route tree and file locations.
2) Implement server component (fetch on server; stream if large).
3) Add client boundary only for interactive bits.
4) Add minimal tests (render + critical behavior).

## Output
- Diff + usage example + accessibility note.
```

### prompts/mui-component.md — MUI v6 component spec

```markdown
# Task: Build/extend a reusable MUI v6 component

## Props
- variant | size | loading | error | aria-* where relevant.
- Strong typing for props; default sensible values; forward refs.

## Requirements
- Accessible by keyboard; focus ring; ARIA labels.
- SSR-safe; no window access in Server Components.
- Story/example snippet and tests for props/edge cases.

## Output
- Component code + small usage snippet + test file skeleton.
```

### prompts/tests.md — Testing playbook

```markdown
# Testing Playbook

## Frontend
- If Vitest present, use it; otherwise Jest. Include react-testing-library.
- Cover: rendering, props, interactions, aria roles, edge cases.
- Avoid flakiness (fake timers, deterministic data).

## Backend
- Pytest with async fixtures; test routes, models, workers.
- Include negative tests (validation/auth).
- For storage: use ephemeral/minio test bucket; clean up.

## Output
- New/updated test files + brief coverage summary.
```

### prompts/observability.md — Sentry + logging

```markdown
# Observability Task

## Goals
- Capture errors to Sentry on both FE/BE.
- Structured logs; no secrets/PII.

## Steps
- Frontend: wrap critical boundaries; add instrumentation.ts hook if missing.
- Backend: init Sentry on startup; set environment, release; capture in exception handlers and worker errors.
- Add breadcrumbs for key flows (uploads, job enqueue/dequeue).

## Output
- Code changes + checklist of signals added.
```

### prompts/storage-minio.md — S3/MinIO upload & retrieval

```markdown
# Storage Task: S3/MinIO upload & retrieval

## Requirements
- Streamed uploads; MIME/type validation; size limits.
- Server-generated, time-limited signed URLs.
- Keys: user/tenant-safe, normalized.

## Steps
1) Server: signer util; PUT/GET presigners with content-type & size constraints.
2) API: route to obtain signed URL; DB record for object metadata.
3) Frontend: upload with fetch (stream if possible); handle 4xx/5xx; show progress.
4) Tests: signer units; API integration; a small end-to-end happy path.

## Output
- Diff + example usage.
```

---

## 3) Examples (how to use with VS Code Copilot Chat)

### Quick start sanity check

```text
@workspace Summarize this repo’s Copilot rules from .github/copilot-instructions.md in 5 bullets. Then wait for my next command.
```

If it can’t see the file, ensure it’s committed at the exact path.

### Use `prompts/review.md`

#### Review – One-liner

```text
@workspace Review #changes using #prompts/review.md. Output: summary + checklist (pass/fail) + concrete follow-ups.
```

#### Review – Expanded

```text
@workspace Review the diffs in #changes guided by #prompts/review.md.
Focus: scope, async FastAPI patterns, Dramatiq idempotency, S3/MinIO streaming, security, tests.
Deliver: (1) 5–10 sentence summary, (2) rubric checklist pass/fail, (3) prioritized follow-ups with file paths.
```

### Use `prompts/fastapi-endpoint.md`

#### FastAPI Endpoint – One-liner

```text
@workspace Implement a POST /api/receipts/validate endpoint in #backend/app/api/receipts.py
using #prompts/fastapi-endpoint.md. Minimal diff + tests. Avoid blocking I/O; offload heavy work to Dramatiq.
```

#### FastAPI Endpoint – Expanded

```text
@workspace Using #prompts/fastapi-endpoint.md:
Task: Add POST /api/receipts/validate that accepts {file_url:string}, enqueues validation, returns {job_id}.
Constraints: async SQLAlchemy session; Pydantic v2 models; raise typed HTTPExceptions; 202 Accepted on enqueue.
Tests: happy path, invalid URL, auth error.
Output: minimal diff + short rationale + assumptions + follow-ups.
```

#### FastAPI Endpoint – Optional top-of-file helper

```text
# <file_spec>
# Task: POST /api/receipts/validate → enqueue Dramatiq job; 202 {job_id}
# Constraints: async session; Pydantic v2; typed errors; no blocking I/O
# Tests: happy, invalid URL, auth
# </file_spec>
```

### Use `prompts/dramatiq-job.md`

#### Dramatiq Job – One-liner

```text
@workspace Create a Dramatiq actor in #backend/app/workers/receipt_tasks.py using #prompts/dramatiq-job.md
to validate a receipt by URL. Add retry/backoff, Sentry logging, and tests for success/retry/poison.
```

#### Dramatiq Job – Expanded

```text
@workspace With #prompts/dramatiq-job.md:
Implement @dramatiq.actor validate_receipt(url: str) → writes result to DB, returns id.
Idempotency: no duplicate records for same (url, hash). Retries on network errors, logs to Sentry.
Provide an enqueue helper used by the API. Output: diff + brief rationale.
```

### Use `prompts/next-page.md` (Next.js App Router)

#### Next.js Page – One-liner

```text
@workspace Build a server component page at #frontend/app/receipts/page.tsx using #prompts/next-page.md
that lists recent receipts (server-side data fetch). Add a small client boundary for a filter form.
```

#### Next.js Page – Expanded

```text
@workspace Apply #prompts/next-page.md:
- Server Component: fetch recent receipts (SSR), stream if large.
- Client Component boundary: simple filter (status/date).
- Keep server actions colocated. Add minimal render test.
Output: diff + usage example + accessibility note.
```

### Use `prompts/mui-component.md` (MUI v6)

#### MUI Component – One-liner

```text
@workspace Create <ReceiptCard/> in #frontend/components/ReceiptCard.tsx using #prompts/mui-component.md.
Props: status, amount, uploadedAt, onClick. Include a usage snippet and a test skeleton.
```

#### MUI Component – Expanded

```text
@workspace Following #prompts/mui-component.md:
- Implement a keyboard-accessible Card with variant, size, loading, error props.
- Strong TypeScript types, forwardRef, aria-* as needed.
- Provide a small example in #frontend/app/receipts/page.tsx and a test skeleton in #frontend/tests/ReceiptCard.test.tsx.
```

### Use `prompts/tests.md`

#### Tests – One-liner

```text
@workspace Generate tests for #backend/app/api/receipts.py and #backend/app/workers/receipt_tasks.py
per #prompts/tests.md. Include negative cases and clean up temp objects/buckets.
```

#### Tests – Expanded

```text
@workspace Use #prompts/tests.md to add:
- Pytest async tests for POST /api/receipts/validate (happy/invalid/auth).
- Worker tests for success, retry, poison.
- Frontend tests for <ReceiptCard/> rendering and keyboard interaction.
Report: list of test files created/modified + brief coverage notes.
```

### Use `prompts/observability.md` (Sentry + logs)

#### Observability – One-liner

```text
@workspace Instrument Sentry on FE/BE and Dramatiq using #prompts/observability.md.
Add structured logs; ensure no PII/secrets in logs. Output code changes + checklist of signals.
```

#### Observability – Expanded

```text
@workspace With #prompts/observability.md:
- Backend: init Sentry on startup, capture in exception handlers; tag env/release.
- Workers: capture exceptions, add breadcrumbs for enqueue/dequeue.
- Frontend: add error boundary and instrumentation hook.
Deliver: diff + checklist of signals added (errors, breadcrumbs, releases).
```

### Use `prompts/storage-minio.md` (S3/MinIO flows)

#### Storage – One-liner

```text
@workspace Implement presigned upload + retrieval using #prompts/storage-minio.md.
Server: signer utils + API route; Frontend: upload with progress; Tests: signer + API integration.
```

#### Storage – Expanded

```text
@workspace Apply #prompts/storage-minio.md:
- Create signer util with content-type and size constraints.
- Add API route to issue time-limited PUT/GET signed URLs, persist metadata.
- FE: implement streamed upload (fetch), show progress and handle 4xx/5xx.
- Tests: signer unit tests; API integration; happy-path e2e.
Output: minimal diffs + example usage.
```

---

## 4) Troubleshooting & Patterns

### Pattern: "Plan → Edit → Summarize" (built into repo instructions)

```text
@workspace Plan → Edit → Summarize.
Use #prompts/fastapi-endpoint.md as the spec. Keep context gathering minimal; act once concrete edits are clear.
Task: <your task>
Constraints: <auth, versions, non-breaking, tests required>
Output: minimal diff + short rationale + follow-ups.
```

### Inline completions boost (optional)

Top-of-file “spec” comments steer inline suggestions while you edit (remove after use):

```ts
// <file_spec>
// Task: Add cursor-based pagination to GET /api/receipts
// Constraints: keep existing response shape; 200ms p95; tests for boundary sizes
// </file_spec>
```

### Commit message prompt

```text
@workspace Propose a conventional commit message for these diffs. Format: type(scope): message + short body + BREAKING CHANGES (if any).
```

**If outputs are too verbose** → “Keep explanation to ≤5 sentences; provide only a minimal unified diff.”  
**If it hesitates** → “Proceed under uncertainty; pick the safest assumption and note it at the end.”  
**If it edits unrelated files** → “Restrict edits to the files listed above; do not refactor beyond scope.”
