"""Tests for the Mahnwesen / dunning engine."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.dunning.engine import (
    compute_drafts,
    interest_amount,
    next_mahnstufe,
)
from mdk_bot.core.models import Invoice, InvoiceStatus


def test_next_mahnstufe_thresholds() -> None:
    assert next_mahnstufe(days_overdue=5, current=0) is None
    assert next_mahnstufe(days_overdue=14, current=0) == 1
    assert next_mahnstufe(days_overdue=30, current=0) == 2
    assert next_mahnstufe(days_overdue=46, current=0) == 3
    assert next_mahnstufe(days_overdue=46, current=2) == 3
    # Already at last stage — no further escalation.
    assert next_mahnstufe(days_overdue=100, current=3) is None


def test_interest_amount_formula() -> None:
    # 1000 EUR × (3.27 + 9)% × 30/365 = 10.0849… → 10.08 after Decimal quantize.
    interest = interest_amount(
        gross=Decimal("1000"),
        days_overdue=30,
        basiszinssatz=Decimal("3.27"),
        margin=Decimal("9"),
    )
    assert interest == Decimal("10.08")


def test_interest_zero_when_not_overdue() -> None:
    assert interest_amount(
        gross=Decimal("1000"),
        days_overdue=0,
        basiszinssatz=Decimal("3"),
        margin=Decimal("9"),
    ) == Decimal("0")


async def test_compute_drafts_skips_not_yet_due(session: AsyncSession) -> None:
    today = date(2026, 5, 19)
    session.add(
        Invoice(
            number="2026-001",
            issue_date=today,
            due_date=today - timedelta(days=5),
            total_gross=500.0,
            status=InvoiceStatus.OPEN,
        )
    )
    await session.commit()
    drafts = await compute_drafts(session, today=today)
    assert drafts == []


async def test_compute_drafts_includes_overdue(session: AsyncSession) -> None:
    today = date(2026, 5, 19)
    session.add(
        Invoice(
            number="2026-001",
            issue_date=today - timedelta(days=20),
            due_date=today - timedelta(days=14),
            total_gross=500.0,
            status=InvoiceStatus.OPEN,
        )
    )
    await session.commit()
    drafts = await compute_drafts(session, today=today)
    assert len(drafts) == 1
    assert drafts[0].mahnstufe == 1
    assert "Zahlungserinnerung" in drafts[0].text


async def test_compute_drafts_stage_3_includes_interest(session: AsyncSession) -> None:
    today = date(2026, 5, 19)
    session.add(
        Invoice(
            number="2026-002",
            issue_date=today - timedelta(days=60),
            due_date=today - timedelta(days=50),
            total_gross=1000.0,
            status=InvoiceStatus.OPEN,
        )
    )
    await session.commit()
    drafts = await compute_drafts(session, today=today)
    assert len(drafts) == 1
    assert drafts[0].mahnstufe == 3
    assert drafts[0].interest > Decimal("0")
    assert drafts[0].fee == Decimal("40.00")  # default fee from config
