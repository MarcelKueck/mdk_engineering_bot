"""Tests for the recurring-expenses capability (engine + CRUD + helpers)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.expenses.engine import (
    effective_amount,
    is_active_on,
    monthly_burn,
    normalize_to_monthly,
)
from mdk_bot.core.models import ExpenseCadence, RecurringExpense


def _expense(**kwargs: object) -> RecurringExpense:
    defaults = {
        "name": "Test",
        "amount": 10.0,
        "currency": "EUR",
        "cadence": ExpenseCadence.MONTHLY,
        "active": True,
    }
    defaults.update(kwargs)
    return RecurringExpense(**defaults)  # type: ignore[arg-type]


def test_is_active_on_respects_window() -> None:
    exp = _expense(effective_from=date(2026, 1, 1), effective_until=date(2026, 12, 31))
    assert is_active_on(exp, date(2026, 6, 1))
    assert not is_active_on(exp, date(2025, 12, 31))
    assert not is_active_on(exp, date(2027, 1, 1))


def test_is_active_on_inactive_flag() -> None:
    assert not is_active_on(_expense(active=False), date(2026, 1, 1))


def test_effective_amount_applies_scheduled_change() -> None:
    exp = _expense(
        amount=10.0,
        next_amount=15.0,
        next_amount_effective_from=date(2026, 8, 1),
    )
    assert effective_amount(exp, date(2026, 7, 31)) == Decimal("10")
    assert effective_amount(exp, date(2026, 8, 1)) == Decimal("15")


@pytest.mark.parametrize(
    "cadence,expected_monthly",
    [
        (ExpenseCadence.MONTHLY, Decimal("12")),
        (ExpenseCadence.QUARTERLY, Decimal("12") / Decimal("3")),
        (ExpenseCadence.YEARLY, Decimal("12") / Decimal("12")),
    ],
)
def test_normalize_to_monthly(cadence: ExpenseCadence, expected_monthly: Decimal) -> None:
    exp = _expense(amount=12.0, cadence=cadence)
    assert normalize_to_monthly(exp, date(2026, 1, 1)) == expected_monthly


async def test_monthly_burn_sums_active_expenses(session: AsyncSession) -> None:
    session.add(_expense(name="A", amount=10.0))
    session.add(_expense(name="B", amount=6.0, cadence=ExpenseCadence.QUARTERLY))  # 2/mo
    session.add(_expense(name="C", amount=120.0, cadence=ExpenseCadence.YEARLY))  # 10/mo
    session.add(_expense(name="D", amount=99.0, active=False))  # ignored
    await session.commit()
    burn = await monthly_burn(session, as_of=date(2026, 5, 19))
    assert burn == Decimal("22.00")


async def test_expense_crud(client: AsyncClient) -> None:
    # Create
    resp = await client.post(
        "/api/v1/expenses",
        json={"name": "Notion", "amount": 9.99, "cadence": "monthly"},
    )
    assert resp.status_code == 201, resp.text
    expense_id = resp.json()["id"]

    # List active
    list_resp = await client.get("/api/v1/expenses", params={"active_only": True})
    assert list_resp.status_code == 200
    assert any(e["id"] == expense_id for e in list_resp.json())

    # Update
    upd = await client.put(f"/api/v1/expenses/{expense_id}", json={"amount": 12.0})
    assert upd.status_code == 200
    assert upd.json()["amount"] == 12.0

    # Delete
    delete_resp = await client.delete(f"/api/v1/expenses/{expense_id}")
    assert delete_resp.status_code == 204


async def test_monthly_burn_endpoint_works(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/expenses",
        json={"name": "X", "amount": 5.0, "cadence": "monthly"},
    )
    resp = await client.get("/api/v1/expenses/_meta/monthly_burn")
    assert resp.status_code == 200
    assert Decimal(resp.json()["monthly_burn"]) >= Decimal("5")
