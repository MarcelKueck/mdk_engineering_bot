"""Read-only audit log view."""

from __future__ import annotations

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.core.models import AuditLog
from mdk_bot.core.schemas import AuditLogRead

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[AuthDep])


@router.get("", response_model=list[AuditLogRead])
async def list_audit(
    session: AsyncSession = SessionDep,
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())
