"""``/anchor <field> <YYYY-MM-DD>`` and ``/anchors`` — manage anchor dates."""

from __future__ import annotations

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import (
    api_client_ctx,
    fmt_http_error,
    operator_handler,
    reply_md,
)


@operator_handler
async def set_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set an anchor date — ``/anchor <field_name> <YYYY-MM-DD>``."""
    args = context.args or []
    if len(args) != 2:
        await reply_md(update, "Usage: `/anchor <field_name> <YYYY-MM-DD>`")
        return
    field_name, value = args
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        await reply_md(update, "Datum muss als `YYYY-MM-DD` angegeben werden.")
        return

    async with api_client_ctx() as api:
        resp = await api.put(f"/anchors/{field_name}", json={"date_value": parsed.isoformat()})
        if resp.status_code != 200:
            await reply_md(update, fmt_http_error(resp))
            return

    await reply_md(update, f"⚓ Anker gesetzt: `{field_name}` = `{parsed.isoformat()}`")


@operator_handler
async def list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List every anchor date currently set."""
    async with api_client_ctx() as api:
        resp = await api.get("/anchors")
        if resp.status_code != 200:
            await reply_md(update, fmt_http_error(resp))
            return

    anchors = resp.json()
    if not anchors:
        await reply_md(update, "Keine Anker gesetzt.")
        return
    lines = ["⚓ *Anker-Daten*", ""]
    for a in anchors:
        lines.append(f"• `{a['field_name']}` = `{a['date_value']}`")
    await reply_md(update, "\n".join(lines))
