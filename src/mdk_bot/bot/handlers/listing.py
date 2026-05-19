"""``/list [category]`` — show the full obligation catalog (optionally filtered)."""

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
    """List obligations grouped by category."""
    args = context.args or []
    category = args[0] if args else None
    params = {"category": category} if category else {}

    async with api_client_ctx() as api:
        resp = await api.get("/obligations", params=params)
        if resp.status_code != 200:
            await reply_md(update, fmt_http_error(resp))
            return

    obligations = resp.json()
    if not obligations:
        await reply_md(update, "No obligations found.")
        return

    header = f"📚 *Catalog* ({category})" if category else "📚 *Catalog*"
    lines = [header, ""]
    last_cat: str | None = None
    for o in obligations:
        if o["category"] != last_cat:
            lines.append(f"_{o['category']}_")
            last_cat = o["category"]
        marker = "⚠️" if o["mandatory"] else "·"
        lines.append(f"{marker} `{o['id']}` — {o['title']}")
    await reply_md(update, "\n".join(lines))
