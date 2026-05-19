"""``/finance`` — finance summary; ``/sync_now`` — trigger Lexware sync."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import (
    api_client_ctx,
    fmt_http_error,
    operator_handler,
    reply,
    reply_md,
)


@operator_handler
async def finance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the finance summary."""
    async with api_client_ctx() as api:
        resp = await api.get("/finance/summary")
    if resp.status_code != 200:
        await reply(update, fmt_http_error(resp))
        return
    body = resp.json()
    if not body.get("lexware_enabled"):
        await reply(
            update,
            f"💼 Lexware not configured: {body.get('lexware_disabled_reason', '?')}",
        )
        return
    lines = [
        "💼 *Finance*",
        "",
        f"Open invoices: {body['open_invoice_count']} (total {body['open_invoice_total']:.2f} EUR)",
        f"Overdue: {body['overdue_invoice_count']}",
    ]
    last = body.get("last_sync_at")
    if last:
        lines.append(f"Last Lexware sync: {last}")
    else:
        lines.append("Lexware sync: not yet run.")
    await reply_md(update, "\n".join(lines))


@operator_handler
async def sync_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger an on-demand Lexware sync."""
    async with api_client_ctx() as api:
        resp = await api.post("/finance/sync")
    if resp.status_code != 200:
        await reply(update, fmt_http_error(resp))
        return
    stats = resp.json()
    lines = ["🔄 *Lexware sync complete*", ""]
    for key, value in stats.items():
        lines.append(f"{key}: {value}")
    await reply_md(update, "\n".join(lines))
