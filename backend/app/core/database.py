"""Database configuration and session management."""

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

# Create async engine with sensible fallbacks; prefer ALEMBIC_DATABASE_URL to avoid drift
alembic_url = os.getenv("ALEMBIC_DATABASE_URL") or getattr(settings, "ALEMBIC_DATABASE_URL", None)
db_url = alembic_url or settings.DATABASE_URL or os.getenv("DATABASE_URL")

if not db_url:
    # Fail fast when fallback is disabled; otherwise use local SQLite for dev.
    if not getattr(settings, "DB_DEV_FALLBACK_SQLITE", False):
        raise RuntimeError(
            "No DATABASE_URL provided and unable to derive from ALEMBIC_DATABASE_URL; "
            "with DB_DEV_FALLBACK_SQLITE=false, a Postgres URL (e.g., Neon) is required."
        )
    db_url = "sqlite+aiosqlite:///./app.db"

engine_kwargs = dict(echo=False, pool_pre_ping=True)
connect_args = {}

try:
    url_obj = make_url(db_url)
except Exception:
    url_obj = None

# Normalize URL to async-friendly driver names
if url_obj is not None:
    driver = url_obj.drivername or ""
    conninfo: Optional[str] = None
    # Upgrade sqlite to aiosqlite for async usage
    if driver == "sqlite":
        url_obj = url_obj.set(drivername="sqlite+aiosqlite")
        db_url = str(url_obj)
    # Ensure Postgres uses an async-capable driver (psycopg supports async in SQLAlchemy 2)
    elif driver in {"postgresql", "postgres", "postgresql+psycopg", "postgresql+psycopg2"}:
        # Normalize to psycopg and ensure channel_binding doesn't block auth
        q = dict(url_obj.query or {})
        if q.get("channel_binding") == "require":
            q["channel_binding"] = "disable"
        elif "channel_binding" not in q:
            q["channel_binding"] = "disable"
        # Keep sslmode=require if present; default to require for Neon
        if not q.get("sslmode"):
            q["sslmode"] = "require"
        url_obj = url_obj.set(drivername="postgresql+psycopg", query=q)
        db_url = str(url_obj)
        # Provide full conninfo so psycopg honors libpq options (prefer the original env DSN)
        conninfo = alembic_url or str(url_obj.set(drivername="postgresql"))
    elif driver == "postgresql+asyncpg":
        # Prefer psycopg for consistency with migrations/worker and Neon channel binding
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

# if url_obj and url_obj.drivername in {"postgresql+asyncpg", "postgresql+psycopg"}:
#     q = dict(url_obj.query)
#     # For psycopg async, sslmode/channel_binding are acceptable; for asyncpg we avoid them.
#     if url_obj.drivername == "postgresql+asyncpg":
#         # Enforce SSL via connect args for asyncpg
#         connect_args["ssl"] = True
#         q.pop("sslmode", None)
#         q.pop("channel_binding", None)
#     # Re-apply sanitized/desired params
#     url_obj = url_obj.set(query=q)
#     db_url = str(url_obj)

# if not db_url.startswith("sqlite+"):
#     engine_kwargs.update(pool_size=10, max_overflow=20)
# Note: URL is safe to log; contains credentials. Avoid logging in production.
# When using psycopg, construct the connection with async_creator using full conninfo.
print(f"Creating async engine with URL: {db_url}")
if conninfo:
    def _async_creator():
        import re
        import psycopg
        # Mask password in logs
        masked = re.sub(r"//([^:]+):[^@]+@", r"//\\1:***@", conninfo)
        print(f"psycopg async conninfo: {masked}")
        return psycopg.AsyncConnection.connect(conninfo=conninfo)
    engine = create_async_engine('postgresql+psycopg://', async_creator=_async_creator, **engine_kwargs)
else:
    engine = create_async_engine(db_url, connect_args=connect_args, **engine_kwargs)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create declarative base
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    global engine, AsyncSessionLocal, USING_SQLITE_FALLBACK, LAST_DB_INIT_ERROR
    try:
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from app.models import tables  # noqa
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        LAST_DB_INIT_ERROR = str(e)
        # Optional dev fallback to SQLite when Neon is unreachable/misconfigured
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
        # We will parse and reconstruct without password.
        url_str = str(engine.url) if hasattr(engine, "url") else db_url
        url_obj = make_url(url_str)
        # Build a masked URL (no password)
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
    except Exception as ex:  # pragma: no cover - defensive
        info.update({"error": f"unable to parse engine url: {ex}"})
    # Also indicate whether related envs exist (booleans only)
    info.update(
        {
            "has_DATABASE_URL_env": bool(os.getenv("DATABASE_URL") or getattr(settings, "DATABASE_URL", None)),
            "has_ALEMBIC_DATABASE_URL_env": bool(os.getenv("ALEMBIC_DATABASE_URL") or getattr(settings, "ALEMBIC_DATABASE_URL", None)),
        }
    )
    return info