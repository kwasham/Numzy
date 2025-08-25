"""Database configuration and session management.

This module constructs an asynchronous SQLAlchemy engine and session
factory for the application.  It prefers the `DATABASE_AUTHENTICATED_URL`
environment variable (or its counterpart on the `Settings` object) when
present.  This allows applications to connect using a restricted
PostgreSQL role (e.g., the `authenticated` role on Neon) for runtime
queries while retaining the ability to run migrations via Alembic using
`ALEMBIC_DATABASE_URL`.  When neither is provided, the traditional
`DATABASE_URL` (or corresponding env var) is used.  A fallback to
SQLite is permitted in development if configured.
"""

from __future__ import annotations

from typing import AsyncGenerator, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import declarative_base
from app.core.config import settings
import os

# Track whether we fell back to SQLite during init
USING_SQLITE_FALLBACK: bool = False
LAST_DB_INIT_ERROR: Optional[str] = None

# -----------------------------------------------------------------------------
# Determine the connection string to use.
#
# Precedence order:
#   1. ALEMBIC_DATABASE_URL – used for migrations and takes priority over all
#      others.  This allows Alembic to run against the owner connection even
#      when the app runs with an authenticated role.
#   2. DATABASE_AUTHENTICATED_URL – when provided, runtime queries will use
#      this connection string.  It should reference a restricted role (e.g.,
#      `authenticated`) that works with Neon row-level security.  If unset,
#      the app falls back to DATABASE_URL.
#   3. DATABASE_URL – the traditional database connection string, typically
#      using the owner/admin role.  Can be set via the Settings class or
#      environment variable.  Only used when neither alembic nor
#      authenticated URLs are provided.
# If all of the above are undefined, a local SQLite database may be used when
# DB_DEV_FALLBACK_SQLITE=true and the environment is development.  Otherwise
# the application will raise an error.

alembic_url = os.getenv("ALEMBIC_DATABASE_URL") or getattr(settings, "ALEMBIC_DATABASE_URL", None)
# Read the authenticated URL from either environment or settings
auth_db_url = os.getenv("DATABASE_AUTHENTICATED_URL") or getattr(settings, "DATABASE_AUTHENTICATED_URL", None)
# Fallback to general database URL
primary_db_url = settings.DATABASE_URL or os.getenv("DATABASE_URL")
db_url = alembic_url or auth_db_url or primary_db_url

if not db_url:
    # Fail fast when no DB URL is provided and fallback is disabled; otherwise
    # use a local SQLite database for development convenience.
    if not getattr(settings, "DB_DEV_FALLBACK_SQLITE", False):
        raise RuntimeError(
            "No database URL provided via ALEMBIC_DATABASE_URL, "
            "DATABASE_AUTHENTICATED_URL or DATABASE_URL; with "
            "DB_DEV_FALLBACK_SQLITE=false, a Postgres URL (e.g., Neon) is required."
        )
    db_url = "sqlite+aiosqlite:///./app.db"

engine_kwargs: dict[str, Any] = dict(echo=False, pool_pre_ping=True)
connect_args: dict[str, Any] = {}

try:
    url_obj = make_url(db_url)
except Exception:
    url_obj = None

# Normalize the driver and query parameters for async usage.  For Postgres
# connections, normalize to use psycopg for async operations and disable
# channel binding.  Always default to sslmode=require when not explicitly
# provided; Neon prefers TLS connections.
conninfo: Optional[str] = None
if url_obj is not None:
    driver = url_obj.drivername or ""
    # SQLite: upgrade to aiosqlite
    if driver == "sqlite":
        url_obj = url_obj.set(drivername="sqlite+aiosqlite")
        db_url = str(url_obj)
    # PostgreSQL: normalize driver and set query params
    elif driver in {"postgresql", "postgres", "postgresql+psycopg", "postgresql+psycopg2"}:
        q = dict(url_obj.query or {})
        # Ensure channel binding doesn't block authentication
        if q.get("channel_binding") == "require":
            q["channel_binding"] = "disable"
        elif "channel_binding" not in q:
            q["channel_binding"] = "disable"
        # Always require SSL unless explicitly disabled
        if not q.get("sslmode"):
            q["sslmode"] = "require"
        url_obj = url_obj.set(drivername="postgresql+psycopg", query=q)
        db_url = str(url_obj)
        # Use the full DSN for psycopg's AsyncConnection to honour libpq options.
        conninfo = alembic_url or str(url_obj.set(drivername="postgresql"))
    # Asyncpg driver: convert to psycopg with similar settings
    elif driver == "postgresql+asyncpg":
        q = dict(url_obj.query or {})
        if q.get("channel_binding") == "require":
            q["channel_binding"] = "disable"
        elif "channel_binding" not in q:
            q["channel_binding"] = "disable"
        if not q.get("sslmode"):
            q["sslmode"] = "require"
        url_obj = url_obj.set(drivername="postgresql+psycopg", query=q)
        db_url = str(url_obj)
        conninfo = alembic_url or str(url_obj.set(drivername="postgresql"))

# Log the selected URL for debugging.  Do not log secrets in production.
print(f"Creating async engine with URL: {db_url}")
if conninfo:
    def _async_creator() -> Any:
        import re
        import psycopg
        # Mask the password in logs
        masked = re.sub(r"//([^:]+):[^@]+@", r"//\\1:***@", conninfo)
        print(f"psycopg async conninfo: {masked}")
        return psycopg.AsyncConnection.connect(conninfo=conninfo)
    engine = create_async_engine('postgresql+psycopg://', async_creator=_async_creator, **engine_kwargs)
else:
    engine = create_async_engine(db_url, connect_args=connect_args, **engine_kwargs)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields a database session.

    This function is intended for FastAPI dependency injection.  Each
    session is scoped to the request and closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables.

    This helper creates all database tables as defined on the declarative
    `Base`.  It is typically called during application startup.  When the
    primary connection fails (e.g., Neon unreachable), this function can
    optionally fall back to a local SQLite database in development as
    controlled by `DB_DEV_FALLBACK_SQLITE`.
    """
    global engine, AsyncSessionLocal, USING_SQLITE_FALLBACK, LAST_DB_INIT_ERROR
    try:
        async with engine.begin() as conn:
            # Import all models to ensure metadata is populated
            from app.models import tables  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        LAST_DB_INIT_ERROR = str(e)
        # Fallback to SQLite when in development and fallback enabled
        if (settings.ENVIRONMENT or "development").lower() == "development" and getattr(settings, "DB_DEV_FALLBACK_SQLITE", True):
            import logging
            logging.getLogger(__name__).warning(f"DB init failed ({e}); falling back to SQLite for development")
            db_url_sqlite = "sqlite+aiosqlite:///./app.db"
            engine = create_async_engine(db_url_sqlite, echo=False, pool_pre_ping=True)
            AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False, autocommit=False, autoflush=False)
            USING_SQLITE_FALLBACK = True
            async with engine.begin() as conn:
                from app.models import tables  # noqa: F401
                await conn.run_sync(Base.metadata.create_all)
        else:
            raise


def get_db_debug_info() -> Dict[str, Any]:
    """Return non-sensitive information about the current DB engine for debugging.

    This avoids leaking passwords or secrets. Intended for a protected/diagnostic endpoint.
    """
    info: Dict[str, Any] = {
        "using_sqlite_fallback": USING_SQLITE_FALLBACK,
        "environment": (settings.ENVIRONMENT or "development"),
    }
    if LAST_DB_INIT_ERROR:
        info["last_db_init_error"] = LAST_DB_INIT_ERROR
    try:
        # engine.url is a SQLAlchemy URL instance; str() will include the password by default.
        # We will parse and reconstruct without the password.
        url_str = str(engine.url) if hasattr(engine, "url") else db_url
        url_obj = make_url(url_str)
        masked_url = url_obj.set(password=None)
        info.update(
            {
                "drivername": url_obj.drivername,
                "username": url_obj.username,
                "host": url_obj.host,
                "port": url_obj.port,
                "database": url_obj.database,
                "query": dict(url_obj.query or {}),
                "url": str(masked_url),
            }
        )
    except Exception as ex:
        info.update({"error": f"unable to parse engine url: {ex}"})
    info.update(
        {
            "has_DATABASE_URL_env": bool(os.getenv("DATABASE_URL") or getattr(settings, "DATABASE_URL", None)),
            "has_ALEMBIC_DATABASE_URL_env": bool(os.getenv("ALEMBIC_DATABASE_URL") or getattr(settings, "ALEMBIC_DATABASE_URL", None)),
            "has_DATABASE_AUTHENTICATED_URL_env": bool(os.getenv("DATABASE_AUTHENTICATED_URL") or getattr(settings, "DATABASE_AUTHENTICATED_URL", None)),
        }
    )
    return info