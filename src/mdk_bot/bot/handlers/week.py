"""``/week`` — obligations + tasks in the next 7 days."""

from __future__ import annotations

from datetime import timedelta

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import (
    api_client_ctx,
    fmt_http_error,
    operator_handler,
    reply_md,
)
from mdk_bot.core.time import today_local


@operator_handler
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List the next week of obligations + tasks."""
    today = today_local()
    horizon = today + timedelta(days=7)
    async with api_client_ctx() as api:
        inst_resp = await api.get("/obligation-instances/upcoming", params={"days": 7})
        if inst_resp.status_code != 200:
            await reply_md(update, fmt_http_error(inst_resp))
            return
        tasks_resp = await api.get("/tasks")
        if tasks_resp.status_code != 200:
            await reply_md(update, fmt_http_error(tasks_resp))
            return

    instances = inst_resp.json()
    tasks = [
        t
        for t in tasks_resp.json()
        if t.get("due_date")
        and today.isoformat() <= t["due_date"] <= horizon.isoformat()
        and t["status"] in ("todo", "doing")
    ]

    lines = [f"📆 *Next 7 days ({today} → {horizon})*", ""]
    if instances:
        lines.append("*Obligations*")
        for inst in instances:
            lines.append(f"• `{inst['due_date']}` — {inst['obligation_id']}")
    if tasks:
        if instances:
            lines.append("")
        lines.append("*Tasks*")
        for task in tasks:
            lines.append(f"• `{task['due_date']}` — {task['title']} (P{task['priority']})")
    if not instances and not tasks:
        lines.append("Nothing in the next 7 days. ✨")

    await reply_md(update, "\n".join(lines))
