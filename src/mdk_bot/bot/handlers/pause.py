"""``/pause [hours]`` and ``/resume`` — silence notifications temporarily."""

from __future__ import annotations

from datetime import timedelta, timezone

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import (
    api_client_ctx,
    fmt_http_error,
    operator_handler,
    reply_md,
)
from mdk_bot.core.time import now_utc


@operator_handler
async def pause_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pause notifications for ``hours`` (default 24)."""
    args = context.args or []
    try:
        hours = int(args[0]) if args else 24
    except ValueError:
        hours = 24
    hours = max(1, min(hours, 24 * 30))
    until = now_utc().astimezone(timezone.utc) + timedelta(hours=hours)

    async with api_client_ctx() as api:
        resp = await api.put(
            "/pause", json={"paused_until": until.isoformat()}
        )
        if resp.status_code != 200:
            await reply_md(update, fmt_http_error(resp))
            return

    await reply_md(update, f"🤫 Bot pausiert bis `{until.isoformat()}`")


@operator_handler
async def resume_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Resume notifications immediately."""
    async with api_client_ctx() as api:
        resp = await api.put("/pause", json={"paused_until": None})
        if resp.status_code != 200:
            await reply_md(update, fmt_http_error(resp))
            return
    await reply_md(update, "▶️ Bot fortgesetzt.")
