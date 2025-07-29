"""Celery worker entrypoint.

Running this module with Celery will start a worker process that
consumes tasks defined in ``app.core.tasks``. You should run

```bash
celery -A receipt_processing_api.worker worker --loglevel=info
```

The Celery application is imported as ``celery_app`` so that Celery
can auto‑discover the registered tasks.
"""

from app.core.tasks import app as celery_app  # noqa: F401

__all__ = ["celery_app"]