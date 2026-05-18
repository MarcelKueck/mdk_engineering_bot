"""Helpers for writing :class:`AuditLog` entries.

Every mutation worth knowing about should call :func:`record`. The log is
append-only — entries are inserted but never updated or deleted.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.core.models import AuditActor, AuditLog


async def record(
    session: AsyncSession,
    *,
    actor: AuditActor,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    """Insert an audit-log row. Caller is responsible for committing."""
    row = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        payload=payload or {},
    )
    session.add(row)
    await session.flush()
    return row
