"""UStVA preview API + approval endpoint."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.capabilities.ustva.engine import (
    compute_payload,
    current_quarter,
    missing_receipts,
)
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, UstvaPeriod, UstvaStatus
from mdk_bot.core.schemas import UstvaPeriodRead
from mdk_bot.core.time import now_utc, today_local

router = APIRouter(prefix="/ustva", tags=["ustva"], dependencies=[AuthDep])


@router.get("", response_model=list[UstvaPeriodRead])
async def list_periods(session: AsyncSession = SessionDep) -> list[UstvaPeriod]:
    rows = (
        (await session.execute(select(UstvaPeriod).order_by(UstvaPeriod.period_start.desc())))
        .scalars()
        .all()
    )
    return list(rows)


@router.post("/prepare", response_model=UstvaPeriodRead)
async def prepare_current(session: AsyncSession = SessionDep) -> UstvaPeriod:
    """Prepare a UStVA preview row for the current quarter (idempotent)."""
    year, quarter, period_start, period_end = current_quarter(today_local())
    stmt = select(UstvaPeriod).where(UstvaPeriod.year == year).where(UstvaPeriod.quarter == quarter)
    period = (await session.execute(stmt)).scalar_one_or_none()
    if period is None:
        period = UstvaPeriod(
            year=year,
            quarter=quarter,
            period_start=period_start,
            period_end=period_end,
            status=UstvaStatus.REVIEW,
        )
        session.add(period)
    payload = await compute_payload(session, period_start=period_start, period_end=period_end)
    gaps = await missing_receipts(session, period_start=period_start, period_end=period_end)
    period.payload = payload.to_dict()
    period.missing_receipts = [g.to_dict() for g in gaps]
    period.status = UstvaStatus.REVIEW
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="ustva.prepared",
        entity_type="ustva_period",
        entity_id=str(period.id),
        payload={"year": year, "quarter": quarter, "missing_count": len(gaps)},
    )
    return period


@router.post("/{period_id}/approve", response_model=UstvaPeriodRead)
async def approve(period_id: UUID, session: AsyncSession = SessionDep) -> UstvaPeriod:
    period = await session.get(UstvaPeriod, period_id)
    if period is None:
        raise HTTPException(status_code=404, detail="ustva period not found")
    period.status = UstvaStatus.APPROVED
    period.approved_at = now_utc()
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="ustva.approved",
        entity_type="ustva_period",
        entity_id=str(period.id),
        payload={"year": period.year, "quarter": period.quarter},
    )
    return period
