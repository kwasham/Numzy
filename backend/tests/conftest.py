from __future__ import annotations

"""Test-level fixtures for async database, user factory, and HTTP client.

Provides:
  - db_session: Async SQLAlchemy session
  - user_factory: creates and persists a User
  - async_client: HTTPX AsyncClient hitting FastAPI app
"""

import asyncio
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.api.main import app
from app.core.config import settings
from app.models.tables import Base, User
from app.models.enums import PlanType


@pytest.fixture(scope="session")
def event_loop():  # override pytest-asyncio strict default loop scope
	loop = asyncio.new_event_loop()
	yield loop
	loop.close()


@pytest.fixture(scope="session")
def _engine():
	# Always use isolated in-memory sqlite for unit tests to avoid touching real Postgres / needing async driver variants.
	url = "sqlite+aiosqlite:///:memory:"
	engine = create_async_engine(url, future=True)
	return engine


@pytest.fixture(scope="session", autouse=True)
async def _create_schema(_engine):
	async with _engine.begin() as conn:
		await conn.run_sync(Base.metadata.create_all)
	yield
	async with _engine.begin() as conn:
		await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture()
async def db_session(_engine):
	async_session_maker = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
	async with async_session_maker() as session:
		yield session


@pytest.fixture()
def user_factory(db_session):
	async def _create(**kwargs):  # returns persisted User
		email = kwargs.pop("email", f"user{__import__('random').randint(1,100000)}@example.com")
		plan = kwargs.pop("plan", PlanType.FREE)
		u = User(email=email, name=kwargs.pop("name", "Test User"), plan=plan)
		for k, v in kwargs.items():
			setattr(u, k, v)
		db_session.add(u)
		await db_session.commit()
		await db_session.refresh(u)
		return u
	return _create


@pytest.fixture()
async def async_client(db_session: AsyncSession):
	# Dependency override for get_db if defined
	try:
		from app.core.database import get_db
		async def override_get_db():
			yield db_session
		app.dependency_overrides[get_db] = override_get_db
	except Exception:
		pass
	async with AsyncClient(app=app, base_url="http://test") as ac:
		yield ac
