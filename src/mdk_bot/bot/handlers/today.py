"""``/today`` — list obligations + tasks due today."""

from __future__ import annotations

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
    """List items due today (obligation instances + tasks)."""
    today = today_local()
    async with api_client_ctx() as api:
        inst_resp = await api.get("/obligation-instances/upcoming", params={"days": 1})
        if inst_resp.status_code != 200:
            await reply_md(update, fmt_http_error(inst_resp))
            return
        tasks_resp = await api.get("/tasks")
        if tasks_resp.status_code != 200:
            await reply_md(update, fmt_http_error(tasks_resp))
            return

    instances = [i for i in inst_resp.json() if i["due_date"] == today.isoformat()]
    tasks = [
        t
        for t in tasks_resp.json()
        if t.get("due_date") == today.isoformat() and t["status"] in ("todo", "doing")
    ]

    lines = [f"📅 *Heute — {today.isoformat()}*", ""]
    if instances:
        lines.append("*Pflichten*")
        for inst in instances:
            lines.append(f"• `{inst['obligation_id']}` — {inst['status']}")
    if tasks:
        if instances:
            lines.append("")
        lines.append("*Tasks*")
        for task in tasks:
            lines.append(f"• {task['title']} (P{task['priority']})")
    if not instances and not tasks:
        lines.append("Nichts heute. ✨")

    await reply_md(update, "\n".join(lines))
