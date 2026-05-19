"""``/send_mahnung <invoice-id-prefix>`` — operator approval to send a draft."""

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
async def send_mahnung(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Find the most recent unsent draft for the given invoice prefix; send it."""
    args = context.args or []
    if not args:
        await reply_md(update, "Usage: `/send_mahnung <invoice-id-prefix>`")
        return
    prefix = args[0]
    async with api_client_ctx() as api:
        runs_resp = await api.get("/dunning/runs")
    if runs_resp.status_code != 200:
        await reply_md(update, fmt_http_error(runs_resp))
        return
    candidate = None
    for run in runs_resp.json():
        if (
            run["invoice_id"].startswith(prefix)
            and run["sent_at"] is None
            and (candidate is None or run["mahnstufe"] > candidate["mahnstufe"])
        ):
            candidate = run
    if candidate is None:
        await reply_md(update, f"No unsent dunning draft for prefix `{prefix}`.")
        return
    async with api_client_ctx() as api:
        resp = await api.post(f"/dunning/{candidate['id']}/send")
    if resp.status_code != 200:
        await reply_md(update, fmt_http_error(resp))
        return
    body = resp.json()
    await reply_md(
        update,
        f'📤 *Mahnung stufe {body["mahnstufe"]} "sent"*\n'
        f"Email transport is stubbed in Phase 2 — logged as a Conversation. "
        f"Gmail send arrives in Phase 3.",
    )
