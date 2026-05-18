"""``/done <obligation_id>`` — mark today's instance done."""

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
    """Find the most-recent open instance for ``obligation_id`` and mark done."""
    args = context.args or []
    if not args:
        await reply_md(update, "Usage: `/done <obligation_id>`")
        return
    obligation_id = args[0]

    async with api_client_ctx() as api:
        resp = await api.get("/obligation-instances/upcoming", params={"days": 365})
        if resp.status_code != 200:
            await reply_md(update, fmt_http_error(resp))
            return
        candidates = [i for i in resp.json() if i["obligation_id"] == obligation_id]
        if not candidates:
            await reply_md(update, f"Keine offene Instanz für `{obligation_id}` gefunden.")
            return
        # Earliest-due, still-open instance first.
        candidates.sort(key=lambda i: i["due_date"])
        instance = candidates[0]
        done_resp = await api.post(f"/obligation-instances/{instance['id']}/done")
        if done_resp.status_code != 200:
            await reply_md(update, fmt_http_error(done_resp))
            return

    await reply_md(
        update,
        f"✅ Erledigt: `{obligation_id}` (Fällig: `{instance['due_date']}`).",
    )
