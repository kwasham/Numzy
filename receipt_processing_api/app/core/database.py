"""Database utilities for the receipt processing API.

This module sets up the SQLAlchemy engine and session makers used
throughout the application. It relies on the configuration defined
in ``app.core.config`` to choose the appropriate database backend.

The database layer uses SQLAlchemy's asynchronous API (``asyncpg``
driver for PostgreSQL or ``aiosqlite`` for SQLite) to avoid
blocking the event loop. A synchronous fallback could be added
later, but asynchronous sessions are recommended when using FastAPI
so that I/O heavy tasks don't block other requests.

Example usage:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

async def list_receipts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Receipt))
    return result.scalars().all()
```
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import settings


# Base declarative class
class Base(DeclarativeBase):
    pass


# Create an asynchronous engine based on the configured database URL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=(settings.ENV == "development"),
    future=True,
)

# Session factory configured for async sessions
async_session_factory = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a new SQLAlchemy session per request.

    This dependency can be injected into FastAPI routes via
    ``Depends(get_db)``. It ensures each request gets its own session
    and closes the session when the request is finished.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialise the database and create all tables.

    This function can be called on application startup. It calls
    ``Base.metadata.create_all`` to create tables based on the ORM
    models defined under ``app.models.tables``. Note that for
    SQLite the database file will be created automatically if it
    does not exist.
    """
    async with engine.begin() as conn:
        # Import models here to ensure they are registered with the
        # metadata before creating tables. Importing inside the
        # function avoids circular import issues.
        from app.models import tables as _tables  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)