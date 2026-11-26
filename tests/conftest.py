"""Pytest fixtures for Protech NAS backend tests.

Uses in-memory SQLite. Models use JSONB from app.models.base which
is a cross-DB TypeDecorator (TEXT on SQLite, JSONB on PostgreSQL).
"""

import os
from collections.abc import AsyncGenerator
from unittest.mock import patch

# The admin API needs a login session or X-API-Key (app/auth.py). Set before the app is imported.
TEST_ADMIN_API_KEY = "test-admin-api-key"
os.environ.setdefault("ADMIN_API_KEY", TEST_ADMIN_API_KEY)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.database import get_db
from app.models.base import Base


# ── DB engine / session ─────────────────────────────────────

@pytest_asyncio.fixture
async def db_engine():
    """In-memory SQLite engine for tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Test DB session — rollback after each test keeps tests isolated."""
    session_factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ── App client ───────────────────────────────────────────────

async def _make_client(db_session, headers: dict) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Disable Jinja2 bytecode cache to avoid Starlette 0.40+ lru_cache
    # keying issues with unhashable context dicts in test environment
    with patch("app.routers.web.templates.env.bytecode_cache", None):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
            headers=headers,
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client with the admin X-API-Key (admin API allowed)."""
    async for ac in _make_client(db_session, {"X-API-Key": TEST_ADMIN_API_KEY}):
        yield ac


@pytest_asyncio.fixture
async def anon_client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client without credentials (like a device or a stranger on the internet)."""
    async for ac in _make_client(db_session, {}):
        yield ac
