"""``/vat <VAT-ID>`` — on-demand qualified VIES check."""

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
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args or []
    if not args:
        await reply_md(update, "Usage: `/vat <VAT-ID>` (e.g. `/vat DE123456789`)")
        return
    vat_id = args[0]
    async with api_client_ctx() as api:
        resp = await api.post("/vies/check", json={"vat_id": vat_id})
    if resp.status_code != 200:
        await reply_md(update, fmt_http_error(resp))
        return
    body = resp.json()
    valid_icon = "✅" if body["valid"] else "❌"
    lines = [
        f"{valid_icon} *VIES check: {body['vat_id_queried']}*",
        "",
        f"Valid: {body['valid']}",
        f"Name match: {body.get('name_match', '-')}",
        f"Address match: {body.get('address_match', '-')}",
        f"Consultation number: `{body.get('consultation_number', '-')}`",
        f"PDF proof: `{body.get('pdf_storage_key', '-')}`",
    ]
    await reply_md(update, "\n".join(lines))
