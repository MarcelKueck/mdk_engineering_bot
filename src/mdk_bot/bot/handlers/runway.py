"""``/runway`` (alias ``/liquidity``) — current liquidity & runway view."""

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
async def show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    async with api_client_ctx() as api:
        resp = await api.get("/liquidity/current")
    if resp.status_code != 200:
        await reply(update, fmt_http_error(resp))
        return
    body = resp.json()
    if not body.get("enabled"):
        await reply(
            update,
            f"💧 Liquidity not configured: {body.get('reason', '?')}\n\n"
            f"Set LIQUIDITY_OPENING_BALANCE and FEATURE_LIQUIDITY=true to enable.",
        )
        return
    lines = [
        "💧 *Liquidity & runway*",
        "",
        f"Opening balance: {body['opening_balance']} EUR",
        f"Monthly burn: {body['monthly_burn']} EUR",
    ]
    if body.get("runway_date"):
        lines.append(f"Covered until: *{body['runway_date']}*")
    else:
        lines.append("Covered: > 18 months (no negative balance projected)")
    if float(body.get("unbilled_potential", 0)) > 0:
        lines.append(f"Potential (unbilled time, NOT committed): {body['unbilled_potential']} EUR")
    inflows = body.get("expected_inflows") or []
    if inflows:
        lines.append("")
        lines.append("*Upcoming inflows*")
        for item in inflows[:10]:
            lines.append(f"• {item['date']}: {item['amount']} EUR — {item.get('label', '')}")
    alerts = body.get("alerts") or []
    for alert in alerts:
        lines.append("")
        lines.append(f"⚠️ {alert.get('kind')}: {alert}")
    await reply_md(update, "\n".join(lines))
