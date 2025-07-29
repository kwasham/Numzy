"""Entry point for the FastAPI application.

This module constructs the FastAPI app, includes all routers and
sets up startup and shutdown events. When run with uvicorn it
initialises the database and loads configuration from
``app.core.config``.
"""

from __future__ import annotations



from fastapi import FastAPI
from app.core.config import settings
import logging
from app.core.database import init_db
from app.api.routes.receipts import router as receipts_router
from app.api.routes.audit_rules import router as audit_rules_router
from app.api.routes.prompts import router as prompts_router
from app.api.routes.evaluations import router as evaluations_router
from app.api.routes.cost_analysis import router as cost_analysis_router
from app.api.routes.users import router as users_router
from app.api.routes.teams import router as teams_router
from fastapi.exception_handlers import RequestValidationError
from app.api.error_handlers import validation_exception_handler, generic_exception_handler



logging.basicConfig(level=logging.INFO)
app = FastAPI(title=settings.APP_NAME)

# Register custom exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include routers
app.include_router(receipts_router)
app.include_router(audit_rules_router)
app.include_router(prompts_router)
app.include_router(evaluations_router)
app.include_router(cost_analysis_router)
app.include_router(users_router)
app.include_router(teams_router)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialise database tables on startup."""
    await init_db()