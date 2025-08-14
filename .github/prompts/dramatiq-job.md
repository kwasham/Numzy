# Task: Add/modify a Dramatiq job

## Requirements

- Idempotent job function (`@dramatiq.actor`), small input payloads.
- Retries/backoff; error logging to Sentry.
- Store results/side effects in DB or object storage, not in memory.

## Steps

1) Define typed payload schema.
2) Implement actor with try/except; raise for retryable errors.
3) Add enqueue helper from API layer; return a job id.
4) Add tests: success, retry, poison message handling.

## Output

- Diff + brief rationale.
