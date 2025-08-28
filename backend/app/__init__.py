"""Top-level application package for the receipt processing API.

This package contains all modules required to run the FastAPI backend
for a modern receipt inspection service. It includes database models,
Pydantic schemas, service layers for extraction, auditing, rule
evaluation, evaluation pipelines, cost analysis and billing stubs, as
well as API routers. The architecture is designed to be modular and
extensible so that individual pieces can be swapped or upgraded
independently.

To run the API locally you can execute:

```bash
uvicorn receipt_processing_api.app.api.main:app --reload
```

This will serve the FastAPI application on http://localhost:8000 and
automatically reload on code changes. The default configuration uses
a local SQLite database stored in ``app.db``. You can override
configuration values using environment variables or a ``.env`` file at
the project root.
"""

__all__: list[str] = []  # explicit for linters; populated dynamically elsewhere if needed