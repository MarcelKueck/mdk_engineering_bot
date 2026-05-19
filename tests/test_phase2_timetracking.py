"""Tests for the timetracking capability."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.timetracking.engine import (
    _window_bounds,
    hours_summary,
    unbilled_value,
)
from mdk_bot.core.models import Project, TimeEntry


def test_window_bounds_week_aligns_to_monday() -> None:
    # 2026-05-19 is a Tuesday → week starts 2026-05-18.
    start, end = _window_bounds(date(2026, 5, 19), "week")
    assert start == date(2026, 5, 18)
    assert end == date(2026, 5, 24)


def test_window_bounds_month() -> None:
    start, end = _window_bounds(date(2026, 2, 15), "month")
    assert start == date(2026, 2, 1)
    assert end == date(2026, 2, 28)


async def test_hours_summary_aggregates(session: AsyncSession) -> None:
    project = Project(name="X")
    session.add(project)
    await session.flush()
    session.add(TimeEntry(date=date(2026, 5, 19), hours=2, project_id=project.id))
    session.add(TimeEntry(date=date(2026, 5, 20), hours=3, billable=False))
    session.add(TimeEntry(date=date(2026, 4, 19), hours=8))  # outside window
    await session.commit()
    summary = await hours_summary(session, as_of=date(2026, 5, 19), window="week")
    assert summary.total == Decimal("5")
    assert summary.billable == Decimal("2")
    assert summary.by_project.get("X") == Decimal("2")


async def test_unbilled_value(session: AsyncSession) -> None:
    project = Project(name="Acme", hourly_rate=100.0)
    session.add(project)
    await session.flush()
    session.add(TimeEntry(date=date(2026, 5, 1), hours=3, project_id=project.id))
    session.add(TimeEntry(date=date(2026, 5, 1), hours=2, project_id=project.id, billed=True))
    session.add(TimeEntry(date=date(2026, 5, 1), hours=10))  # no project — skipped
    await session.commit()
    value = await unbilled_value(session, as_of=date(2026, 5, 19))
    assert value == Decimal("300.00")


async def test_log_and_summary_via_api(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/time", json={"date": "2026-05-19", "hours": 1.5})
    assert resp.status_code == 201, resp.text

    sumr = await client.get("/api/v1/time/_meta/summary", params={"window": "week"})
    assert sumr.status_code == 200
    assert Decimal(sumr.json()["total_hours"]) >= Decimal("1.5")
