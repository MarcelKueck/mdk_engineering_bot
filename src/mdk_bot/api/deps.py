"""Shared FastAPI dependencies — DB session, auth, redis."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.core.auth import require_session
from mdk_bot.core.db import get_sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session that commits on success."""
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


AuthDep = Depends(require_session)
SessionDep = Depends(get_session)
