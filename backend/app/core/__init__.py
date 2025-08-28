"""Core application services and infrastructure layer.

Exports configuration settings and frequently used helpers to simplify import
paths inside tests (e.g. `from app.core import settings`).
"""

from .config import settings  # noqa: F401