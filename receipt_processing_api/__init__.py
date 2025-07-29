"""Root package for the receipt processing API.

Declaring this file allows Python to recognise the
``receipt_processing_api`` directory as a package so that modules
inside it can be imported using dotted paths. Without this file
``app.*`` imports would fail.
"""

import sys as _sys
from importlib import import_module as _import_module

# Alias the internal ``app`` package so that absolute imports like
# ``from app.core.database import ...`` work correctly. Without this
# alias Python would try to resolve ``app`` as a top-level module and
# fail. When this package is imported it automatically registers
# ``receipt_processing_api.app`` as ``app`` in ``sys.modules``.
_sys.modules.setdefault("app", _import_module("receipt_processing_api.app"))

__all__ = []