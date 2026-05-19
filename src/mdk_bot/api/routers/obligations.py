"""Read-only obligation catalog + instance state transitions."""

from __future__ import annotations

from datetime import UTC, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.core.audit import record
from mdk_bot.core.models import (
    AdhocRules,
    AuditActor,
    Obligation,
    ObligationInstance,
    ObligationInstanceStatus,
    PauseState,
)
from mdk_bot.core.schemas import ObligationInstanceRead, ObligationRead
from mdk_bot.core.time import now_utc, today_local

router = APIRouter(prefix="/obligations", tags=["obligations"], dependencies=[AuthDep])


@router.get("", response_model=list[ObligationRead])
async def list_obligations(
    session: AsyncSession = SessionDep,
    category: str | None = None,
) -> list[Obligation]:
    stmt = select(Obligation).order_by(Obligation.id)
    if category:
        stmt = stmt.where(Obligation.category == category)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/adhoc")
async def list_adhoc_rules(session: AsyncSession = SessionDep) -> list[dict[str, Any]]:
    """Return the ad-hoc rule catalog (transcribed from obligations.json)."""
    row = await session.get(AdhocRules, 1)
    return row.payload if row else []


@router.get("/{obligation_id}", response_model=ObligationRead)
async def get_obligation(obligation_id: str, session: AsyncSession = SessionDep) -> Obligation:
    obligation = await session.get(Obligation, obligation_id)
    if obligation is None:
        raise HTTPException(status_code=404, detail="obligation not found")
    return obligation


instances_router = APIRouter(
    prefix="/obligation-instances", tags=["obligations"], dependencies=[AuthDep]
)


@instances_router.get("/upcoming", response_model=list[ObligationInstanceRead])
async def upcoming_instances(
    session: AsyncSession = SessionDep, days: int = Query(default=7, ge=1, le=365)
) -> list[ObligationInstance]:
    cutoff = today_local() + timedelta(days=days)
    stmt = (
        select(ObligationInstance)
        .where(ObligationInstance.due_date <= cutoff)
        .where(
            ObligationInstance.status.in_(
                [
                    ObligationInstanceStatus.PENDING,
                    ObligationInstanceStatus.NOTIFIED,
                    ObligationInstanceStatus.ESCALATED,
                ]
            )
        )
        .order_by(ObligationInstance.due_date.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


@instances_router.post("/{instance_id}/done", response_model=ObligationInstanceRead)
async def mark_done(instance_id: UUID, session: AsyncSession = SessionDep) -> ObligationInstance:
    instance = await session.get(ObligationInstance, instance_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="instance not found")
    instance.status = ObligationInstanceStatus.DONE
    instance.acknowledged_at = now_utc()
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="obligation_instance.done",
        entity_type="obligation_instance",
        entity_id=str(instance.id),
        payload={"obligation_id": instance.obligation_id},
    )
    return instance


@instances_router.post("/{instance_id}/skip", response_model=ObligationInstanceRead)
async def mark_skip(instance_id: UUID, session: AsyncSession = SessionDep) -> ObligationInstance:
    instance = await session.get(ObligationInstance, instance_id)
    if instance is None:
        raise HTTPException(status_code=404, detail="instance not found")
    instance.status = ObligationInstanceStatus.SKIPPED
    instance.acknowledged_at = now_utc()
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="obligation_instance.skip",
        entity_type="obligation_instance",
        entity_id=str(instance.id),
        payload={"obligation_id": instance.obligation_id},
    )
    return instance


pause_router = APIRouter(prefix="/pause", tags=["bot"], dependencies=[AuthDep])


@pause_router.get("")
async def get_pause(session: AsyncSession = SessionDep) -> dict[str, Any]:
    row = await session.get(PauseState, 1)
    return {"paused_until": row.paused_until.isoformat() if row and row.paused_until else None}


@pause_router.put("", status_code=status.HTTP_200_OK)
async def set_pause(payload: dict[str, Any], session: AsyncSession = SessionDep) -> dict[str, Any]:
    from datetime import datetime

    until = payload.get("paused_until")
    parsed: datetime | None = None
    if until:
        parsed = datetime.fromisoformat(until)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
    row = await session.get(PauseState, 1)
    if row is None:
        row = PauseState(id=1, paused_until=parsed)
        session.add(row)
    else:
        row.paused_until = parsed
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="bot.pause" if parsed else "bot.resume",
        entity_type="pause_state",
        entity_id="1",
        payload={"paused_until": parsed.isoformat() if parsed else None},
    )
    return {"paused_until": parsed.isoformat() if parsed else None}
