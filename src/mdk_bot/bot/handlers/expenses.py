"""``/expenses`` family — list, add, edit, remove recurring expenses."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import UUID

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import (
    api_client_ctx,
    fmt_http_error,
    operator_handler,
    reply_md,
)


@operator_handler
async def list_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List active recurring expenses + monthly total."""
    async with api_client_ctx() as api:
        resp = await api.get("/expenses", params={"active_only": True})
        burn_resp = await api.get("/expenses/_meta/monthly_burn")
    if resp.status_code != 200:
        await reply_md(update, fmt_http_error(resp))
        return
    items = resp.json()
    lines = ["📒 *Recurring expenses*", ""]
    for item in items:
        lines.append(
            f"• `{item['id'][:8]}` {item['name']} — "
            f"{item['amount']} {item['currency']}/{item['cadence']}"
        )
    if not items:
        lines.append("(none)")
    if burn_resp.status_code == 200:
        burn = burn_resp.json()
        lines.append("")
        lines.append(f"_Monthly burn:_ *{burn['monthly_burn']} EUR*")
    await reply_md(update, "\n".join(lines))


def _parse_amount(text: str) -> Decimal | None:
    try:
        return Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None


@operator_handler
async def add_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/expense_add <name> <amount> [cadence]`` — default cadence monthly."""
    args = context.args or []
    if len(args) < 2:
        await reply_md(update, "Usage: `/expense_add <name> <amount> [monthly|quarterly|yearly]`")
        return
    cadence = "monthly"
    if args[-1].lower() in {"monthly", "quarterly", "yearly"}:
        cadence = args[-1].lower()
        amount_str = args[-2]
        name = " ".join(args[:-2])
    else:
        amount_str = args[-1]
        name = " ".join(args[:-1])
    amount = _parse_amount(amount_str)
    if amount is None or not name:
        await reply_md(update, "Could not parse amount or name.")
        return
    async with api_client_ctx() as api:
        resp = await api.post(
            "/expenses",
            json={"name": name, "amount": float(amount), "cadence": cadence},
        )
    if resp.status_code != 201:
        await reply_md(update, fmt_http_error(resp))
        return
    body = resp.json()
    await reply_md(
        update,
        f"✅ Added `{body['id'][:8]}` {body['name']} ({body['amount']} {body['cadence']})",
    )


@operator_handler
async def edit_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/expense_edit <id-prefix> <amount>`` — update the active amount."""
    args = context.args or []
    if len(args) < 2:
        await reply_md(update, "Usage: `/expense_edit <id-prefix> <amount>`")
        return
    prefix, amount_str = args[0], args[1]
    amount = _parse_amount(amount_str)
    if amount is None:
        await reply_md(update, "Could not parse amount.")
        return
    expense_id = await _resolve_prefix(prefix)
    if expense_id is None:
        await reply_md(update, f"No expense found with prefix `{prefix}`.")
        return
    async with api_client_ctx() as api:
        resp = await api.put(f"/expenses/{expense_id}", json={"amount": float(amount)})
    if resp.status_code != 200:
        await reply_md(update, fmt_http_error(resp))
        return
    body = resp.json()
    await reply_md(update, f"✏️ Updated `{body['id'][:8]}` → {body['amount']} EUR")


@operator_handler
async def rm_expense(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/expense_rm <id-prefix>`` — deactivate (soft delete)."""
    args = context.args or []
    if not args:
        await reply_md(update, "Usage: `/expense_rm <id-prefix>`")
        return
    expense_id = await _resolve_prefix(args[0])
    if expense_id is None:
        await reply_md(update, f"No expense found with prefix `{args[0]}`.")
        return
    async with api_client_ctx() as api:
        resp = await api.put(f"/expenses/{expense_id}", json={"active": False})
    if resp.status_code != 200:
        await reply_md(update, fmt_http_error(resp))
        return
    await reply_md(update, f"🗑 Deactivated `{str(expense_id)[:8]}`.")


async def _resolve_prefix(prefix: str) -> UUID | None:
    async with api_client_ctx() as api:
        resp = await api.get("/expenses")
    if resp.status_code != 200:
        return None
    for item in resp.json():
        if item["id"].startswith(prefix):
            return UUID(item["id"])
    return None
