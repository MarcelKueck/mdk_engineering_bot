"""Shared pytest fixtures.

Tests use an in-memory SQLite database via aiosqlite. Models switch to
generic JSON/Uuid types on non-Postgres dialects (see ``models.py``), so
the schema can be created via ``Base.metadata.create_all`` without
running the Alembic migration.
"""

from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DATABASE_URL_SYNC", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("WEB_SESSION_TOKEN", "test-web-token")
os.environ.setdefault("INTERNAL_API_TOKEN", "test-internal-token")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("AUTHORIZED_TELEGRAM_USER_ID", "42")
os.environ.setdefault("ENVIRONMENT", "test")

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from mdk_bot.api.app import create_app
from mdk_bot.api.deps import get_session
from mdk_bot.config import get_settings
from mdk_bot.core import db as core_db
from mdk_bot.core.db import Base
from mdk_bot.core.models import *  # noqa: F403  -- register tables on Base.metadata


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """Fresh in-memory SQLite engine, one per test."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def sessionmaker_(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def session(
    sessionmaker_: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with sessionmaker_() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def client(
    engine: AsyncEngine,
    sessionmaker_: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    """FastAPI test client with the test engine wired in."""
    # Make get_engine/get_sessionmaker return the test ones.
    core_db._engine = engine  # type: ignore[attr-defined]
    core_db._sessionmaker = sessionmaker_  # type: ignore[attr-defined]

    app = create_app()

    async def _override_session() -> AsyncIterator[AsyncSession]:
        async with sessionmaker_() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_session] = _override_session

    transport = ASGITransport(app=app)
    settings = get_settings()
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    core_db._engine = None  # type: ignore[attr-defined]
    core_db._sessionmaker = None  # type: ignore[attr-defined]


@pytest.fixture
def auth_cookie() -> dict[str, str]:
    """Return cookie dict with a valid signed session for /web/ access."""
    from mdk_bot.core.auth import SESSION_COOKIE, issue_session

    return {SESSION_COOKIE: issue_session()}
