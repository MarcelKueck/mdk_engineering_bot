"""Liquidity snapshots API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.capabilities.liquidity.engine import compute_snapshot, is_enabled
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, LiquiditySnapshot
from mdk_bot.core.schemas import LiquiditySnapshotRead
from mdk_bot.core.time import today_local

router = APIRouter(prefix="/liquidity", tags=["liquidity"], dependencies=[AuthDep])


@router.get("/snapshots", response_model=list[LiquiditySnapshotRead])
async def list_snapshots(session: AsyncSession = SessionDep) -> list[LiquiditySnapshot]:
    rows = (
        (
            await session.execute(
                select(LiquiditySnapshot).order_by(LiquiditySnapshot.created_at.desc()).limit(20)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


@router.get("/current")
async def current(session: AsyncSession = SessionDep) -> dict[str, object]:
    enabled, reason = is_enabled()
    if not enabled:
        return {"enabled": False, "reason": reason}
    snap = await compute_snapshot(session, as_of=today_local())
    return {
        "enabled": True,
        "opening_balance": str(snap.opening_balance),
        "monthly_burn": str(snap.monthly_burn),
        "runway_date": snap.runway_date.isoformat() if snap.runway_date else None,
        "unbilled_potential": str(snap.unbilled_potential),
        "scheduled_outflows": snap.scheduled_outflows,
        "expected_inflows": snap.expected_inflows,
        "alerts": snap.alerts,
    }


@router.post("/snapshots", response_model=LiquiditySnapshotRead)
async def create_snapshot(session: AsyncSession = SessionDep) -> LiquiditySnapshot:
    enabled, reason = is_enabled()
    if not enabled:
        raise HTTPException(status_code=400, detail=f"Liquidity disabled: {reason}")
    comp = await compute_snapshot(session, as_of=today_local())
    snap = LiquiditySnapshot(
        opening_balance=float(comp.opening_balance),
        runway_date=comp.runway_date,
        scheduled_outflows=comp.scheduled_outflows,
        expected_inflows=comp.expected_inflows,
        alerts=comp.alerts,
    )
    session.add(snap)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="liquidity.snapshot.created",
        entity_type="liquidity_snapshot",
        entity_id=str(snap.id),
        payload={"runway_date": snap.runway_date.isoformat() if snap.runway_date else None},
    )
    return snap
