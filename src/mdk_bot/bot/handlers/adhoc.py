"""``/adhoc`` — list ad-hoc rules from the catalog."""

from __future__ import annotations

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
    """Show every ad-hoc rule as a quick reference."""
    async with api_client_ctx() as api:
        resp = await api.get("/obligations/adhoc")
        if resp.status_code != 200:
            await reply_md(update, fmt_http_error(resp))
            return
    rules = resp.json()
    if not rules:
        await reply_md(update, "No ad-hoc rules defined.")
        return
    lines = ["📐 *Ad-hoc rules*", ""]
    for rule in rules:
        lines.append(f"• *{rule.get('title', rule.get('id'))}* (`{rule.get('id')}`)")
        if rule.get("trigger"):
            lines.append(f"   _Trigger:_ {rule['trigger']}")
        if rule.get("action"):
            lines.append(f"   _Action:_ {rule['action']}")
        lines.append("")
    await reply_md(update, "\n".join(lines))
