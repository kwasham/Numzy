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
