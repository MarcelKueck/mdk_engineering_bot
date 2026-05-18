"""End-to-end style tests for the daily-check engine."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.bot.notifier import RecordingNotifier
from mdk_bot.capabilities.reminders.engine import run_daily_check
from mdk_bot.core.models import (
    AnchorDate,
    ObligationInstance,
    ObligationInstanceStatus,
)
from tests.factories import make_obligation


@pytest.mark.parametrize(
    "today,due,lead_time,should_notify",
    [
        (date(2025, 4, 3), date(2025, 4, 10), 7, True),  # exactly lead-time
        (date(2025, 4, 2), date(2025, 4, 10), 7, False),  # outside window
        (date(2025, 4, 10), date(2025, 4, 10), 7, True),  # due today
    ],
)
async def test_daily_check_lead_time_window(
    session: AsyncSession,
    today: date,
    due: date,
    lead_time: int,
    should_notify: bool,
) -> None:
    obligation = make_obligation(
        id="ustva_quartal",
        recurrence=f"FREQ=YEARLY;BYMONTH={due.month};BYMONTHDAY={due.day}",
        lead_time_days=lead_time,
    )
    session.add(obligation)
    await session.flush()

    notifier = RecordingNotifier()
    stats = await run_daily_check(session, notifier, today=today)
    if should_notify:
        assert stats["notified"] == 1
        assert len(notifier.messages) == 1
        assert "ustva_quartal" in notifier.messages[0] or "USt-Voranmeldung" in notifier.messages[0]
    else:
        assert stats["notified"] == 0
        assert notifier.messages == []


async def test_daily_check_is_idempotent_same_day(session: AsyncSession) -> None:
    obligation = make_obligation(recurrence="FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=10", lead_time_days=7)
    session.add(obligation)
    await session.flush()

    notifier = RecordingNotifier()
    await run_daily_check(session, notifier, today=date(2025, 4, 3))
    await run_daily_check(session, notifier, today=date(2025, 4, 3))
    assert len(notifier.messages) == 1


async def test_daily_check_re_notifies_next_day(session: AsyncSession) -> None:
    obligation = make_obligation(recurrence="FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=10", lead_time_days=7)
    session.add(obligation)
    await session.flush()

    notifier = RecordingNotifier()
    await run_daily_check(session, notifier, today=date(2025, 4, 3))
    await run_daily_check(session, notifier, today=date(2025, 4, 4))
    assert len(notifier.messages) == 2


async def test_daily_check_escalates_overdue_mandatory(session: AsyncSession) -> None:
    obligation = make_obligation(
        recurrence="FREQ=YEARLY;BYMONTH=4;BYMONTHDAY=10",
        lead_time_days=0,
        mandatory=True,
    )
    session.add(obligation)
    await session.flush()

    notifier = RecordingNotifier()
    await run_daily_check(session, notifier, today=date(2025, 4, 11))
    instance = (await session.execute(select(ObligationInstance))).scalar_one()
    assert instance.status == ObligationInstanceStatus.ESCALATED
    assert "PFLICHT" in notifier.messages[0]


async def test_anchor_driven_requires_anchor(session: AsyncSession) -> None:
    obligation = make_obligation(
        id="berufshaftpflicht_verlaengerung",
        recurrence="FREQ=YEARLY",
        lead_time_days=60,
        mandatory=True,
        anchor_date_field="vertragsablauf_berufshaftpflicht",
    )
    session.add(obligation)
    await session.flush()

    notifier = RecordingNotifier()
    # Monday 2025-04-07 — should send anchor-missing nudge
    stats = await run_daily_check(session, notifier, today=date(2025, 4, 7))
    assert stats["anchor_missing"] == 1
    assert "vertragsablauf_berufshaftpflicht" in notifier.messages[0]


async def test_anchor_driven_with_anchor(session: AsyncSession) -> None:
    obligation = make_obligation(
        id="berufshaftpflicht_verlaengerung",
        recurrence="FREQ=YEARLY",
        lead_time_days=60,
        mandatory=True,
        anchor_date_field="vertragsablauf_berufshaftpflicht",
    )
    anchor = AnchorDate(
        field_name="vertragsablauf_berufshaftpflicht",
        date_value=date(2027, 1, 15),
    )
    session.add_all([obligation, anchor])
    await session.flush()

    notifier = RecordingNotifier()
    # 60 days before 2027-01-15 = 2026-11-16 (Mon, no holiday).
    notify_day = date(2027, 1, 15) - timedelta(days=60)
    stats = await run_daily_check(session, notifier, today=notify_day)
    assert stats["notified"] == 1
    instance = (await session.execute(select(ObligationInstance))).scalar_one()
    assert instance.due_date == date(2027, 1, 15)
