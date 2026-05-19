"""``/details <id>`` — print everything we know about a single obligation."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import (
    api_client_ctx,
    fmt_http_error,
    operator_handler,
    reply_md,
)


@operator_handler
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show the raw record for an obligation id."""
    args = context.args or []
    if not args:
        await reply_md(update, "Usage: `/details <obligation_id>`")
        return
    obligation_id = args[0]

    async with api_client_ctx() as api:
        resp = await api.get(f"/obligations/{obligation_id}")
        if resp.status_code == 404:
            await reply_md(update, f"Unknown ID: `{obligation_id}`")
            return
        if resp.status_code != 200:
            await reply_md(update, fmt_http_error(resp))
            return

    o = resp.json()
    pretty = json.dumps(o["raw"], indent=2, ensure_ascii=False)
    text = (
        f"*{o['title']}*\n"
        f"Category: `{o['category']}` · Mandatory: {'yes' if o['mandatory'] else 'no'}\n"
        f"Recurrence: `{o['recurrence']}`\n"
        f"Lead time: {o['lead_time_days']}d · Effort: ~{o['estimated_minutes']} min\n"
        f"Tool: {o['tool']}\n\n"
        f"```\n{pretty}\n```"
    )
    await reply_md(update, text)
