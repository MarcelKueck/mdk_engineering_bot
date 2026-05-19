"""CRUD + summaries for :class:`TimeEntry`."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.capabilities.timetracking.engine import (
    hours_summary,
    unbilled_value,
)
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, TimeEntry
from mdk_bot.core.schemas import TimeEntryCreate, TimeEntryRead, TimeEntryUpdate
from mdk_bot.core.time import today_local

router = APIRouter(prefix="/time", tags=["time-tracking"], dependencies=[AuthDep])


@router.get("", response_model=list[TimeEntryRead])
async def list_entries(
    session: AsyncSession = SessionDep,
    unbilled_only: bool = False,
) -> list[TimeEntry]:
    stmt = select(TimeEntry).order_by(TimeEntry.date.desc(), TimeEntry.created_at.desc())
    if unbilled_only:
        stmt = stmt.where(TimeEntry.billable.is_(True)).where(TimeEntry.billed.is_(False))
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


def _remap_entry_date(data: dict[str, object]) -> dict[str, object]:
    """``entry_date`` is the Python field name; the ORM column is ``date``."""
    if "entry_date" in data:
        data["date"] = data.pop("entry_date")
    return data


@router.post("", response_model=TimeEntryRead, status_code=status.HTTP_201_CREATED)
async def create_entry(payload: TimeEntryCreate, session: AsyncSession = SessionDep) -> TimeEntry:
    entry = TimeEntry(**_remap_entry_date(payload.model_dump()))
    session.add(entry)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="time_entry.create",
        entity_type="time_entry",
        entity_id=str(entry.id),
        payload={"date": entry.date.isoformat(), "hours": str(entry.hours)},
    )
    return entry


@router.put("/{entry_id}", response_model=TimeEntryRead)
async def update_entry(
    entry_id: UUID, payload: TimeEntryUpdate, session: AsyncSession = SessionDep
) -> TimeEntry:
    entry = await session.get(TimeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="time entry not found")
    changes = _remap_entry_date(payload.model_dump(exclude_unset=True))
    for key, value in changes.items():
        setattr(entry, key, value)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="time_entry.update",
        entity_type="time_entry",
        entity_id=str(entry.id),
        payload={k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in changes.items()},
    )
    return entry


@router.post("/{entry_id}/mark_billed", response_model=TimeEntryRead)
async def mark_billed(
    entry_id: UUID,
    invoice_id: UUID | None = None,
    session: AsyncSession = SessionDep,
) -> TimeEntry:
    entry = await session.get(TimeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="time entry not found")
    entry.billed = True
    if invoice_id is not None:
        entry.invoice_id = invoice_id
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="time_entry.mark_billed",
        entity_type="time_entry",
        entity_id=str(entry.id),
        payload={"invoice_id": str(invoice_id) if invoice_id else None},
    )
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: UUID, session: AsyncSession = SessionDep) -> None:
    entry = await session.get(TimeEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="time entry not found")
    await session.delete(entry)
    await record(
        session,
        actor=AuditActor.USER,
        action="time_entry.delete",
        entity_type="time_entry",
        entity_id=str(entry_id),
    )


@router.get("/_meta/summary")
async def summary_endpoint(
    session: AsyncSession = SessionDep,
    window: Literal["week", "month"] = "week",
) -> dict[str, object]:
    summary = await hours_summary(session, as_of=today_local(), window=window)
    return {
        "window": window,
        "period_start": summary.period_start.isoformat(),
        "period_end": summary.period_end.isoformat(),
        "total_hours": str(summary.total),
        "billable_hours": str(summary.billable),
        "billed_hours": str(summary.billed),
        "by_project": {k: str(v) for k, v in summary.by_project.items()},
    }


@router.get("/_meta/unbilled")
async def unbilled_endpoint(session: AsyncSession = SessionDep) -> dict[str, str]:
    value = await unbilled_value(session, as_of=today_local())
    return {"unbilled_value": str(value), "currency": "EUR"}
