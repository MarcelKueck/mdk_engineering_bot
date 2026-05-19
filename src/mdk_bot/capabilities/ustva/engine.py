"""Compute a UStVA preview from synced Lexware data + check completeness."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.expenses.engine import is_active_on
from mdk_bot.config import get_settings
from mdk_bot.core.models import (
    Invoice,
    Receipt,
    RecurringExpense,
)


def is_enabled() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.FEATURE_USTVA:
        return False, "FEATURE_USTVA=false"
    return True, ""


@dataclass(frozen=True)
class UstvaPayload:
    """Computed figures for one quarter."""

    output_vat: Decimal
    input_vat: Decimal
    revenue_net: Decimal
    expense_net: Decimal
    balance: Decimal

    def to_dict(self) -> dict[str, str]:
        return {
            "output_vat": str(self.output_vat),
            "input_vat": str(self.input_vat),
            "revenue_net": str(self.revenue_net),
            "expense_net": str(self.expense_net),
            "balance": str(self.balance),
        }


@dataclass(frozen=True)
class Belegcheck:
    """One missing-receipt entry returned by :func:`missing_receipts`."""

    expense_id: str
    name: str
    expected_total: Decimal

    def to_dict(self) -> dict[str, str]:
        return {
            "expense_id": self.expense_id,
            "name": self.name,
            "expected_total": str(self.expected_total),
        }


def current_quarter(as_of: date) -> tuple[int, int, date, date]:
    """Return ``(year, quarter, period_start, period_end)`` for ``as_of``."""
    quarter = (as_of.month - 1) // 3 + 1
    start_month = (quarter - 1) * 3 + 1
    period_start = date(as_of.year, start_month, 1)
    end_month = start_month + 2
    last_day = monthrange(as_of.year, end_month)[1]
    period_end = date(as_of.year, end_month, last_day)
    return as_of.year, quarter, period_start, period_end


def _decimal(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


async def compute_payload(
    session: AsyncSession, *, period_start: date, period_end: date
) -> UstvaPayload:
    """Compute output/input VAT and net figures from synced Lexware data."""
    invoice_stmt = (
        select(Invoice)
        .where(Invoice.issue_date >= period_start)
        .where(Invoice.issue_date <= period_end)
    )
    invoices = (await session.execute(invoice_stmt)).scalars().all()
    receipt_stmt = (
        select(Receipt).where(Receipt.date >= period_start).where(Receipt.date <= period_end)
    )
    receipts = (await session.execute(receipt_stmt)).scalars().all()

    revenue_net = sum((_decimal(i.total_net) for i in invoices), Decimal("0"))
    revenue_gross = sum((_decimal(i.total_gross) for i in invoices), Decimal("0"))
    output_vat = revenue_gross - revenue_net

    expense_net = sum((_decimal(r.total) - _decimal(r.vat) for r in receipts), Decimal("0"))
    input_vat = sum((_decimal(r.vat) for r in receipts), Decimal("0"))

    return UstvaPayload(
        output_vat=output_vat.quantize(Decimal("0.01")),
        input_vat=input_vat.quantize(Decimal("0.01")),
        revenue_net=revenue_net.quantize(Decimal("0.01")),
        expense_net=expense_net.quantize(Decimal("0.01")),
        balance=(output_vat - input_vat).quantize(Decimal("0.01")),
    )


async def missing_receipts(
    session: AsyncSession, *, period_start: date, period_end: date
) -> list[Belegcheck]:
    """For every active vat-rate-tagged recurring expense, check the period.

    A "match" is any Receipt within the period whose ``vendor_org_id`` lines
    up with the expense's vendor, OR whose category equals the expense
    category and whose total is within 1% of the expected monthly amount.
    The heuristic is intentionally loose — false positives just suppress
    a nudge, false negatives are surfaced to the operator who decides.
    """
    expenses = (await session.execute(select(RecurringExpense))).scalars().all()
    receipts = (
        (
            await session.execute(
                select(Receipt)
                .where(Receipt.date >= period_start)
                .where(Receipt.date <= period_end)
            )
        )
        .scalars()
        .all()
    )
    matched_keys: set[tuple[object, str]] = set()
    for receipt in receipts:
        matched_keys.add((receipt.vendor_org_id, receipt.category or ""))
    gaps: list[Belegcheck] = []
    months_in_period = max(
        1, (period_end.year - period_start.year) * 12 + period_end.month - period_start.month + 1
    )
    for expense in expenses:
        if expense.vat_rate is None:
            continue
        if not is_active_on(expense, period_start):
            continue
        expected_monthly = Decimal(str(expense.amount))
        expected_total = (expected_monthly * Decimal(months_in_period)).quantize(Decimal("0.01"))
        if (expense.vendor_org_id, expense.category or "") in matched_keys:
            continue
        # Fall-back fuzzy match by total within the period
        ok = False
        for receipt in receipts:
            if receipt.total is None:
                continue
            diff = abs(Decimal(str(receipt.total)) - expected_monthly)
            if diff <= expected_monthly * Decimal("0.01"):
                ok = True
                break
        if ok:
            continue
        gaps.append(
            Belegcheck(
                expense_id=str(expense.id),
                name=expense.name,
                expected_total=expected_total,
            )
        )
    return gaps


def days_until_quarter_end(as_of: date) -> int:
    _, _, _, period_end = current_quarter(as_of)
    return (period_end - as_of).days


def is_in_preview_window(as_of: date, *, lead_days: int = 7) -> bool:
    """True iff today is within ``lead_days`` of the current quarter end."""
    return 0 <= days_until_quarter_end(as_of) <= lead_days


def previous_quarter(as_of: date) -> tuple[int, int, date, date]:
    """The quarter that JUST ended — used by the scheduler in early Apr/Jul/etc."""
    last_q_end = date(as_of.year, ((as_of.month - 1) // 3) * 3 + 1, 1) - timedelta(days=1)
    return current_quarter(last_q_end)
