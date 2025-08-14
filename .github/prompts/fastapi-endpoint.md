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
