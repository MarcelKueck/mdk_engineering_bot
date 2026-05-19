"""``/upcoming [N]`` — list the next N obligation instances."""

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
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the next N instances. ``N`` defaults to 5."""
    args = context.args or []
    try:
        count = int(args[0]) if args else 5
    except ValueError:
        count = 5
    count = max(1, min(count, 50))

    async with api_client_ctx() as api:
        resp = await api.get("/obligation-instances/upcoming", params={"days": 365})
        if resp.status_code != 200:
            await reply(update, fmt_http_error(resp))
            return

    instances = resp.json()[:count]
    if not instances:
        await reply_md(update, "No upcoming instances. ✨")
        return

    lines = [f"📋 *Next {len(instances)} instances*", ""]
    for inst in instances:
        lines.append(f"`{inst['due_date']}` — `{inst['obligation_id']}` ({inst['status']})")
    await reply_md(update, "\n".join(lines))
