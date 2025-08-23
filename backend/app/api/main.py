"""Entry point for the FastAPI application.

This module constructs the FastAPI app, includes all routers and
sets up startup and shutdown events. When run with uvicorn it
initialises the database and loads configuration from
``app.core.config``.
"""

from __future__ import annotations



from fastapi import FastAPI, Request, Depends
from fastapi.security import HTTPBearer
from app.core.config import settings
from app.core.observability import init_sentry
import logging
from app.core.database import init_db, get_db_debug_info
from app.api.routes.receipts import router as receipts_router
from app.api.routes.audit_rules import router as audit_rules_router
from app.api.routes.prompts import router as prompts_router
from app.api.routes.evaluations import router as evaluations_router
from app.api.routes.cost_analysis import router as cost_analysis_router
from app.api.routes.users import router as users_router
from app.api.routes.teams import router as teams_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.events import router as events_router
from app.api.routes.stripe_webhooks import router as stripe_webhooks_router
from app.api.routes.billing import router as billing_router
from fastapi.exception_handlers import RequestValidationError
from app.api.error_handlers import validation_exception_handler, generic_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from urllib.parse import urlparse
from contextlib import asynccontextmanager
import os

try:  # optional import for typing / scope usage
    import sentry_sdk  # type: ignore
except Exception:  # pragma: no cover
    sentry_sdk = None  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("Starting up...")
    # Centralised Sentry init (idempotent)
    if init_sentry("api"):
        logger.info("Sentry SDK initialized (api)")
    await init_db()
    yield
    # Shutdown
    logger.info("Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Numzy API",
    version="1.0.0",
    lifespan=lifespan,
)


# Middleware to enrich Sentry scope with lightweight request + user info
@app.middleware("http")
async def sentry_context_middleware(request: Request, call_next):  # type: ignore
    if sentry_sdk and settings.SENTRY_DSN:
        with sentry_sdk.configure_scope() as scope:  # type: ignore
            scope.set_tag("path", request.url.path)
            scope.set_tag("method", request.method)
            # Attempt to pull user id from header (lightweight) before auth dependency runs
            uid = request.headers.get("x-user-id") or request.headers.get("x-user")
            if uid:
                scope.user = {"id": uid}
    response = await call_next(request)
    return response

"""CORS configuration.

Logic:
1. In development => allow all ( * ) for simplest DX.
2. Otherwise start from BACKEND_CORS_ORIGINS.
3. Ensure the FRONTEND_BASE_URL origin is present (parsed) when not wildcard.
4. Deduplicate while preserving order.
"""
env_is_dev = (settings.ENVIRONMENT or "development").lower() == "development"
allow_origins = ["*"] if env_is_dev else list(settings.BACKEND_CORS_ORIGINS or [])

if not env_is_dev:
    try:
        parsed = urlparse(getattr(settings, "FRONTEND_BASE_URL", ""))
        if parsed.scheme and parsed.netloc:
            front_origin = f"{parsed.scheme}://{parsed.netloc}"
            if "*" not in allow_origins and front_origin not in allow_origins:
                allow_origins.append(front_origin)
    except Exception:
        pass

# Always ensure common localhost dev origins present unless wildcard already used
if "*" not in allow_origins:
    for dev_origin in ["http://localhost:3000", "http://127.0.0.1:3000"]:
        if dev_origin not in allow_origins:
            allow_origins.append(dev_origin)

# Deduplicate preserving order
seen = set()
allow_origins = [o for o in allow_origins if not (o in seen or seen.add(o))]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
app.include_router(teams_router, prefix="/teams", tags=["teams"])
app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
app.include_router(events_router)
app.include_router(stripe_webhooks_router)
app.include_router(billing_router)

# Quietly absorb Chrome devtools /.well-known probe (prevents 404 log noise)
@app.get("/.well-known/appspecific/com.chrome.devtools.json", include_in_schema=False)
async def chrome_devtools_probe():  # pragma: no cover - minimal utility endpoint
    return {}

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Welcome to Numzy Receipt Processing API"}


@app.get("/auth-test")
def auth_test(credentials=Depends(HTTPBearer())):
    return {"message": "You are authorized"}


@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    """Health check endpoint (supports GET & HEAD)."""
    return {"status": "healthy"}


@app.get("/debug/db")
async def db_debug():
    """Return non-sensitive DB diagnostics (for development)."""
    return get_db_debug_info()


@app.post("/debug/sentry")
async def sentry_test():
    """Intentionally raise an error to verify Sentry backend wiring (dev only)."""
    if (settings.ENVIRONMENT or "development").lower() != "development":
        return {"ok": False, "message": "disabled in non-development env"}
    raise RuntimeError("Sentry backend test exception")