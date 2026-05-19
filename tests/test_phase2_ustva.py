"""Tests for the UStVA engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.ustva.engine import (
    compute_payload,
    current_quarter,
    days_until_quarter_end,
    is_in_preview_window,
    missing_receipts,
    previous_quarter,
)
from mdk_bot.core.models import (
    ExpenseCadence,
    Invoice,
    InvoiceStatus,
    Receipt,
    RecurringExpense,
)


@pytest.mark.parametrize(
    "today,expected_quarter,expected_start,expected_end",
    [
        (date(2026, 1, 15), 1, date(2026, 1, 1), date(2026, 3, 31)),
        (date(2026, 5, 19), 2, date(2026, 4, 1), date(2026, 6, 30)),
        (date(2026, 9, 30), 3, date(2026, 7, 1), date(2026, 9, 30)),
        (date(2026, 12, 31), 4, date(2026, 10, 1), date(2026, 12, 31)),
    ],
)
def test_current_quarter(
    today: date, expected_quarter: int, expected_start: date, expected_end: date
) -> None:
    year, quarter, start, end = current_quarter(today)
    assert year == 2026
    assert quarter == expected_quarter
    assert start == expected_start
    assert end == expected_end


def test_previous_quarter() -> None:
    year, quarter, start, end = previous_quarter(date(2026, 4, 3))
    assert (year, quarter) == (2026, 1)
    assert start == date(2026, 1, 1)
    assert end == date(2026, 3, 31)


def test_preview_window() -> None:
    # Q2 ends June 30; today is June 25 — within 7-day lead.
    assert is_in_preview_window(date(2026, 6, 25), lead_days=7)
    assert not is_in_preview_window(date(2026, 6, 20), lead_days=7)


def test_days_until_quarter_end() -> None:
    assert days_until_quarter_end(date(2026, 6, 30)) == 0
    assert days_until_quarter_end(date(2026, 6, 25)) == 5


async def test_compute_payload_from_synced_data(session: AsyncSession) -> None:
    session.add(
        Invoice(
            issue_date=date(2026, 5, 1),
            total_gross=119.0,
            total_net=100.0,
            status=InvoiceStatus.OPEN,
        )
    )
    session.add(Receipt(date=date(2026, 5, 2), total=119.0, vat=19.0))
    await session.commit()
    payload = await compute_payload(
        session, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
    )
    assert payload.output_vat == Decimal("19.00")
    assert payload.input_vat == Decimal("19.00")
    assert payload.balance == Decimal("0.00")


async def test_missing_receipts_flags_gap(session: AsyncSession) -> None:
    session.add(
        RecurringExpense(
            name="Hetzner",
            amount=5.65,
            cadence=ExpenseCadence.MONTHLY,
            vat_rate=19.0,
        )
    )
    await session.commit()
    gaps = await missing_receipts(
        session, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
    )
    assert len(gaps) == 1
    assert gaps[0].name == "Hetzner"


async def test_missing_receipts_skipped_when_receipt_present(
    session: AsyncSession,
) -> None:
    session.add(
        RecurringExpense(
            name="Hetzner",
            amount=5.65,
            cadence=ExpenseCadence.MONTHLY,
            vat_rate=19.0,
        )
    )
    session.add(Receipt(date=date(2026, 5, 1), total=5.65, vat=0.90))
    await session.commit()
    gaps = await missing_receipts(
        session, period_start=date(2026, 4, 1), period_end=date(2026, 6, 30)
    )
    assert gaps == []
