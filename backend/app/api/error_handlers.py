"""
Custom exception handlers for FastAPI.
Provides clear, actionable error messages for validation and server errors.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import RequestValidationError
from fastapi.exceptions import HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY, HTTP_500_INTERNAL_SERVER_ERROR
from app.core.config import settings

try:
    import sentry_sdk  # type: ignore
    _SENTRY_AVAILABLE = True
except Exception:  # pragma: no cover - optional
    _SENTRY_AVAILABLE = False


def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "body": exc.body,
        },
    )


def generic_exception_handler(request: Request, exc: Exception):
    # Best-effort capture to Sentry if configured
    if _SENTRY_AVAILABLE and settings.SENTRY_DSN:
        try:
            sentry_sdk.capture_exception(exc)
        except Exception:
            pass
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "details": str(exc),
        },
    )

# Usage in main.py:
# from app.api.error_handlers import validation_exception_handler, generic_exception_handler
# app.add_exception_handler(RequestValidationError, validation_exception_handler)
# app.add_exception_handler(Exception, generic_exception_handler)
