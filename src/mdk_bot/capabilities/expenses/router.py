"""CRUD API for :class:`RecurringExpense`."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.capabilities.expenses.engine import monthly_burn
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, RecurringExpense
from mdk_bot.core.schemas import (
    RecurringExpenseCreate,
    RecurringExpenseRead,
    RecurringExpenseUpdate,
)
from mdk_bot.core.time import today_local

router = APIRouter(prefix="/expenses", tags=["recurring-expenses"], dependencies=[AuthDep])


@router.get("", response_model=list[RecurringExpenseRead])
async def list_expenses(
    session: AsyncSession = SessionDep, active_only: bool = False
) -> list[RecurringExpense]:
    stmt = select(RecurringExpense).order_by(RecurringExpense.name)
    if active_only:
        stmt = stmt.where(RecurringExpense.active.is_(True))
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


@router.post("", response_model=RecurringExpenseRead, status_code=status.HTTP_201_CREATED)
async def create_expense(
    payload: RecurringExpenseCreate, session: AsyncSession = SessionDep
) -> RecurringExpense:
    expense = RecurringExpense(**payload.model_dump())
    session.add(expense)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="expense.create",
        entity_type="recurring_expense",
        entity_id=str(expense.id),
        payload={"name": expense.name, "amount": str(expense.amount)},
    )
    return expense


@router.get("/{expense_id}", response_model=RecurringExpenseRead)
async def get_expense(expense_id: UUID, session: AsyncSession = SessionDep) -> RecurringExpense:
    expense = await session.get(RecurringExpense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="expense not found")
    return expense


@router.put("/{expense_id}", response_model=RecurringExpenseRead)
async def update_expense(
    expense_id: UUID,
    payload: RecurringExpenseUpdate,
    session: AsyncSession = SessionDep,
) -> RecurringExpense:
    expense = await session.get(RecurringExpense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="expense not found")
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(expense, key, value)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="expense.update",
        entity_type="recurring_expense",
        entity_id=str(expense.id),
        payload={k: (v.value if hasattr(v, "value") else v) for k, v in changes.items()},
    )
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(expense_id: UUID, session: AsyncSession = SessionDep) -> None:
    expense = await session.get(RecurringExpense, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="expense not found")
    await session.delete(expense)
    await record(
        session,
        actor=AuditActor.USER,
        action="expense.delete",
        entity_type="recurring_expense",
        entity_id=str(expense_id),
    )


@router.get("/_meta/monthly_burn")
async def monthly_burn_endpoint(
    session: AsyncSession = SessionDep,
) -> dict[str, str]:
    burn = await monthly_burn(session, as_of=today_local())
    return {"monthly_burn": str(burn), "currency": "EUR"}
