"""``/ustva`` — show current preview; ``/approve_ustva`` — operator approval."""

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
async def show(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prepare + show the current UStVA preview."""
    async with api_client_ctx() as api:
        resp = await api.post("/ustva/prepare")
    if resp.status_code != 200:
        await reply_md(update, fmt_http_error(resp))
        return
    period = resp.json()
    payload = period.get("payload") or {}
    lines = [
        f"📊 *UStVA Q{period['quarter']}/{period['year']}*",
        f"({period['period_start']} → {period['period_end']})",
        "",
        f"Output VAT: {payload.get('output_vat', '0')} EUR",
        f"Input VAT: {payload.get('input_vat', '0')} EUR",
        f"Zahllast: {payload.get('balance', '0')} EUR",
        f"Status: {period['status']}",
    ]
    gaps = period.get("missing_receipts") or []
    if gaps:
        lines.append("")
        lines.append(f"⚠️ {len(gaps)} missing receipts:")
        for gap in gaps[:10]:
            lines.append(f"• {gap['name']} (~{gap['expected_total']} EUR)")
    lines.append("")
    lines.append(f"Approve with `/approve_ustva {period['id'][:8]}`")
    await reply_md(update, "\n".join(lines))


@operator_handler
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/approve_ustva [<id-prefix>]`` — approve the most recent preview."""
    args = context.args or []
    async with api_client_ctx() as api:
        list_resp = await api.get("/ustva")
    if list_resp.status_code != 200:
        await reply_md(update, fmt_http_error(list_resp))
        return
    periods = list_resp.json()
    if not periods:
        await reply_md(update, "No UStVA preview exists yet. Run `/ustva` first.")
        return
    if args:
        period = next((p for p in periods if p["id"].startswith(args[0])), None)
        if period is None:
            await reply_md(update, f"No period with prefix `{args[0]}`.")
            return
    else:
        period = periods[0]
    async with api_client_ctx() as api:
        approve_resp = await api.post(f"/ustva/{period['id']}/approve")
    if approve_resp.status_code != 200:
        await reply_md(update, fmt_http_error(approve_resp))
        return
    await reply_md(
        update,
        f"✅ Q{period['quarter']}/{period['year']} approved.\n\n"
        f"_Phase 2 stops here — submit the actual UStVA to ELSTER manually "
        f"in Lexware. Auto-submit ships in a later phase._",
    )
