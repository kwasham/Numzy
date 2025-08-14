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
