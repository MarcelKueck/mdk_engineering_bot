"""Domain helpers for :class:`TimeEntry` — summary, unbilled value."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.core.models import Project, TimeEntry

Window = Literal["week", "month"]


@dataclass(frozen=True)
class HoursSummary:
    """Aggregated hours for a window — feeds ``/hours``."""

    period_start: date
    period_end: date
    total: Decimal
    billable: Decimal
    billed: Decimal
    by_project: dict[str, Decimal]


def _window_bounds(as_of: date, window: Window) -> tuple[date, date]:
    if window == "week":
        start = as_of - timedelta(days=as_of.weekday())
        end = start + timedelta(days=6)
        return start, end
    start = as_of.replace(day=1)
    if start.month == 12:
        next_first = start.replace(year=start.year + 1, month=1)
    else:
        next_first = start.replace(month=start.month + 1)
    end = next_first - timedelta(days=1)
    return start, end


async def hours_summary(
    session: AsyncSession, *, as_of: date, window: Window = "week"
) -> HoursSummary:
    start, end = _window_bounds(as_of, window)
    rows = (
        (
            await session.execute(
                select(TimeEntry).where(TimeEntry.date >= start).where(TimeEntry.date <= end)
            )
        )
        .scalars()
        .all()
    )
    projects = {p.id: p.name for p in (await session.execute(select(Project))).scalars().all()}
    total = Decimal("0")
    billable_total = Decimal("0")
    billed_total = Decimal("0")
    by_project: dict[str, Decimal] = {}
    for entry in rows:
        hrs = Decimal(str(entry.hours))
        total += hrs
        if entry.billable:
            billable_total += hrs
        if entry.billed:
            billed_total += hrs
        project_name = projects.get(entry.project_id) if entry.project_id else "(no project)"
        by_project[project_name or "(no project)"] = (
            by_project.get(project_name or "(no project)", Decimal("0")) + hrs
        )
    return HoursSummary(
        period_start=start,
        period_end=end,
        total=total,
        billable=billable_total,
        billed=billed_total,
        by_project=by_project,
    )


async def unbilled_value(session: AsyncSession, *, as_of: date) -> Decimal:
    """Sum (hours × project hourly_rate) for billable, unbilled entries.

    Entries without a project or without an hourly_rate are skipped — we
    have no defensible price for them. ``as_of`` only matters once we
    add a "stop counting after N days" rule; today it is a no-op kept
    for signature parity with other engines.
    """
    del as_of
    rows = (
        (
            await session.execute(
                select(TimeEntry)
                .where(TimeEntry.billable.is_(True))
                .where(TimeEntry.billed.is_(False))
            )
        )
        .scalars()
        .all()
    )
    project_rates: dict[object, Decimal | None] = {}
    total = Decimal("0")
    for entry in rows:
        if entry.project_id is None:
            continue
        if entry.project_id not in project_rates:
            project = await session.get(Project, entry.project_id)
            project_rates[entry.project_id] = (
                Decimal(str(project.hourly_rate))
                if project is not None and project.hourly_rate is not None
                else None
            )
        rate = project_rates[entry.project_id]
        if rate is None:
            continue
        total += Decimal(str(entry.hours)) * rate
    return total.quantize(Decimal("0.01"))
