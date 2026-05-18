"""Anchor date CRUD (user-set dates that drive yearly obligations)."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.core.audit import record
from mdk_bot.core.models import AnchorDate, AuditActor
from mdk_bot.core.schemas import AnchorDateRead, AnchorDateUpdate
from mdk_bot.core.time import now_utc

router = APIRouter(prefix="/anchors", tags=["anchors"], dependencies=[AuthDep])


@router.get("", response_model=list[AnchorDateRead])
async def list_anchors(session: AsyncSession = SessionDep) -> list[AnchorDate]:
    result = await session.execute(select(AnchorDate).order_by(AnchorDate.field_name))
    return list(result.scalars().all())


@router.put("/{field_name}", response_model=AnchorDateRead)
async def set_anchor(
    field_name: str,
    payload: AnchorDateUpdate,
    session: AsyncSession = SessionDep,
) -> AnchorDate:
    anchor = await session.get(AnchorDate, field_name)
    if anchor is None:
        anchor = AnchorDate(
            field_name=field_name,
            date_value=payload.date_value,
            set_by=payload.set_by,
        )
        session.add(anchor)
    else:
        anchor.date_value = payload.date_value
        anchor.set_by = payload.set_by
        anchor.set_at = now_utc()
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="anchor.set",
        entity_type="anchor_date",
        entity_id=field_name,
        payload={"date_value": payload.date_value.isoformat()},
    )
    return anchor
