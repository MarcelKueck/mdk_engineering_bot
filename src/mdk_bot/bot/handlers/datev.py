"""``/datev_export <year>`` — generate a DATEV CSV + metadata pack."""

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
async def export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args or not args[0].isdigit():
        await reply_md(update, "Usage: `/datev_export <year>` (e.g. `/datev_export 2025`)")
        return
    year = int(args[0])
    async with api_client_ctx() as api:
        resp = await api.post(f"/datev/export/{year}")
    if resp.status_code != 200:
        await reply(update, fmt_http_error(resp))
        return
    body = resp.json()
    await reply_md(
        update,
        f"📦 *DATEV export {year}*\n\n"
        f"CSV: `{body['csv_path']}`\n"
        f"Meta: `{body['metadata_path']}`\n"
        f"Invoices: {body['invoice_count']} · Receipts: {body['receipt_count']}",
    )
