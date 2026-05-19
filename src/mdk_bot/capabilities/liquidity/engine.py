"""Compute a runway view: opening balance + dated outflows/inflows."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.expenses.engine import monthly_burn
from mdk_bot.config import get_settings
from mdk_bot.core.models import Invoice, InvoiceStatus


def is_enabled() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.FEATURE_LIQUIDITY:
        return False, "FEATURE_LIQUIDITY=false"
    if Decimal("0") >= settings.LIQUIDITY_OPENING_BALANCE:
        return False, "LIQUIDITY_OPENING_BALANCE not set"
    return True, ""


@dataclass(frozen=True)
class LiquidityComputation:
    """One liquidity calculation — what the weekly snapshot persists."""

    opening_balance: Decimal
    monthly_burn: Decimal
    scheduled_outflows: list[dict[str, Any]]
    expected_inflows: list[dict[str, Any]]
    runway_date: date | None
    unbilled_potential: Decimal
    alerts: list[dict[str, Any]]


def _end_of_month(d: date) -> date:
    last = monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last)


async def _open_invoices(
    session: AsyncSession,
) -> list[tuple[date, Decimal, str | None]]:
    """Return (due_date, gross, label) for every still-open invoice with a due date."""
    rows = (
        (
            await session.execute(
                select(Invoice).where(
                    Invoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.OVERDUE])
                )
            )
        )
        .scalars()
        .all()
    )
    out: list[tuple[date, Decimal, str | None]] = []
    for inv in rows:
        if inv.due_date is None or inv.total_gross is None:
            continue
        out.append((inv.due_date, Decimal(str(inv.total_gross)), inv.number))
    return out


def _project_until(
    *,
    opening_balance: Decimal,
    monthly_burn: Decimal,
    steuerrate: Decimal,
    expected_inflows: list[tuple[date, Decimal]],
    as_of: date,
    horizon_days: int = 540,
) -> date | None:
    """Walk forward day-by-day; return the first date balance goes negative.

    On the 1st of each month: subtract the monthly burn and the
    Steuerrücklage rate × revenue received in the previous month.
    """
    balance = opening_balance
    inflow_by_date: dict[date, Decimal] = {}
    for d, amount in expected_inflows:
        inflow_by_date[d] = inflow_by_date.get(d, Decimal("0")) + amount
    revenue_this_month = Decimal("0")
    cursor = as_of
    for _ in range(horizon_days):
        balance += inflow_by_date.get(cursor, Decimal("0"))
        revenue_this_month += inflow_by_date.get(cursor, Decimal("0"))
        if balance < Decimal("0"):
            return cursor
        # End-of-month bookkeeping: charge the next day's outflows.
        if cursor == _end_of_month(cursor):
            balance -= monthly_burn
            balance -= revenue_this_month * steuerrate
            revenue_this_month = Decimal("0")
        cursor += timedelta(days=1)
    return None


async def compute_snapshot(session: AsyncSession, *, as_of: date) -> LiquidityComputation:
    """Compute everything the weekly snapshot needs."""
    from mdk_bot.capabilities.timetracking.engine import unbilled_value

    settings = get_settings()
    opening = Decimal(str(settings.LIQUIDITY_OPENING_BALANCE))
    burn = await monthly_burn(session, as_of=as_of)
    invoices = await _open_invoices(session)
    invoices.sort()

    expected_inflows_data = [
        {"date": d.isoformat(), "amount": str(amt), "label": f"Invoice {label or '?'}"}
        for d, amt, label in invoices
    ]

    # Outflows: a 12-month projection of the monthly burn for transparency.
    scheduled: list[dict[str, Any]] = []
    cursor = _end_of_month(as_of)
    for _ in range(12):
        scheduled.append(
            {
                "date": cursor.isoformat(),
                "amount": str(burn),
                "label": "Monthly burn (recurring expenses)",
            }
        )
        next_month = cursor + timedelta(days=1)
        cursor = _end_of_month(next_month)

    runway = _project_until(
        opening_balance=opening,
        monthly_burn=burn,
        steuerrate=Decimal(str(settings.STEUERRUECKLAGE_RATE)),
        expected_inflows=[(d, amt) for d, amt, _ in invoices],
        as_of=as_of,
    )

    alerts: list[dict[str, Any]] = []
    if runway is not None:
        days = (runway - as_of).days
        if days <= settings.LIQUIDITY_RUNWAY_WARNING_DAYS:
            alerts.append(
                {
                    "kind": "runway_short",
                    "days": days,
                    "runway_date": runway.isoformat(),
                }
            )

    unbilled = await unbilled_value(session, as_of=as_of)

    return LiquidityComputation(
        opening_balance=opening,
        monthly_burn=burn,
        scheduled_outflows=scheduled,
        expected_inflows=expected_inflows_data,
        runway_date=runway,
        unbilled_potential=unbilled,
        alerts=alerts,
    )
