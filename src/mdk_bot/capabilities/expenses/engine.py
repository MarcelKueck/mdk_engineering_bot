"""Pure domain helpers for :class:`RecurringExpense`.

Anything that touches money is computed with :class:`Decimal`. Cadence
normalisation: monthly = ×1, quarterly = ÷3, yearly = ÷12.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.core.models import ExpenseCadence, RecurringExpense

_CADENCE_TO_MONTHLY: dict[ExpenseCadence, Decimal] = {
    ExpenseCadence.MONTHLY: Decimal("1"),
    ExpenseCadence.QUARTERLY: Decimal("1") / Decimal("3"),
    ExpenseCadence.YEARLY: Decimal("1") / Decimal("12"),
}


def is_active_on(expense: RecurringExpense, as_of: date) -> bool:
    """Return True iff ``expense`` is active on ``as_of`` per its window."""
    if not expense.active:
        return False
    if expense.effective_from is not None and as_of < expense.effective_from:
        return False
    return not (expense.effective_until is not None and as_of > expense.effective_until)


def effective_amount(expense: RecurringExpense, as_of: date) -> Decimal:
    """Return the active amount on ``as_of`` (scheduled price-change aware)."""
    if (
        expense.next_amount is not None
        and expense.next_amount_effective_from is not None
        and as_of >= expense.next_amount_effective_from
    ):
        return Decimal(str(expense.next_amount))
    return Decimal(str(expense.amount))


def normalize_to_monthly(expense: RecurringExpense, as_of: date) -> Decimal:
    """Return ``expense``'s contribution to the monthly burn on ``as_of``."""
    if not is_active_on(expense, as_of):
        return Decimal("0")
    return effective_amount(expense, as_of) * _CADENCE_TO_MONTHLY[expense.cadence]


async def monthly_burn(session: AsyncSession, *, as_of: date) -> Decimal:
    """Sum every active expense, normalised to a monthly EUR figure.

    Currency mixing is intentionally NOT supported: every expense is
    summed as if it were EUR. The seed data is all EUR; the operator
    handles non-EUR cases manually until a multi-currency layer lands.
    """
    rows = (await session.execute(select(RecurringExpense))).scalars().all()
    total = Decimal("0")
    for expense in rows:
        total += normalize_to_monthly(expense, as_of)
    return total.quantize(Decimal("0.01"))
