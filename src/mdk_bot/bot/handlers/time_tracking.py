"""Time-tracking commands — ``/log``, ``/hours``, ``/unbilled``."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import (
    api_client_ctx,
    fmt_http_error,
    operator_handler,
    reply_md,
)
from mdk_bot.core.time import today_local


def _parse_hours(text: str) -> Decimal | None:
    try:
        value = Decimal(text.replace(",", "."))
    except InvalidOperation:
        return None
    if value <= 0:
        return None
    return value


@operator_handler
async def log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/log <hours> [project-prefix] [note...]`` — quick entry, date=today."""
    args = context.args or []
    if not args:
        await reply_md(update, "Usage: `/log <hours> [project-prefix] [note...]`")
        return
    hours = _parse_hours(args[0])
    if hours is None:
        await reply_md(update, "Could not parse hours.")
        return
    project_id = None
    note: str | None = None
    if len(args) >= 2:
        async with api_client_ctx() as api:
            proj_resp = await api.get("/projects")
        if proj_resp.status_code == 200:
            for p in proj_resp.json():
                if p["id"].startswith(args[1]) or args[1].lower() in p["name"].lower():
                    project_id = p["id"]
                    break
        if project_id is None:
            note = " ".join(args[1:])
        elif len(args) > 2:
            note = " ".join(args[2:])
    payload = {
        "date": today_local().isoformat(),
        "hours": float(hours),
    }
    if project_id is not None:
        payload["project_id"] = project_id
    if note is not None:
        payload["note"] = note
    async with api_client_ctx() as api:
        resp = await api.post("/time", json=payload)
    if resp.status_code != 201:
        await reply_md(update, fmt_http_error(resp))
        return
    await reply_md(update, f"⏱ Logged {hours}h.")


@operator_handler
async def hours(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/hours [week|month]`` — summary."""
    args = context.args or []
    window = args[0].lower() if args else "week"
    if window not in {"week", "month"}:
        window = "week"
    async with api_client_ctx() as api:
        resp = await api.get("/time/_meta/summary", params={"window": window})
    if resp.status_code != 200:
        await reply_md(update, fmt_http_error(resp))
        return
    body = resp.json()
    lines = [
        f"⏱ *Hours — this {window}*",
        f"({body['period_start']} → {body['period_end']})",
        "",
        f"Total: {body['total_hours']}h",
        f"Billable: {body['billable_hours']}h",
        f"Billed: {body['billed_hours']}h",
    ]
    if body["by_project"]:
        lines.append("")
        lines.append("*By project:*")
        for name, hrs in body["by_project"].items():
            lines.append(f"• {name}: {hrs}h")
    await reply_md(update, "\n".join(lines))


@operator_handler
async def unbilled(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """``/unbilled`` — entries marked billable but not yet billed."""
    async with api_client_ctx() as api:
        list_resp = await api.get("/time", params={"unbilled_only": True})
        value_resp = await api.get("/time/_meta/unbilled")
    if list_resp.status_code != 200:
        await reply_md(update, fmt_http_error(list_resp))
        return
    entries = list_resp.json()
    by_project: dict[str, float] = {}
    for entry in entries:
        project_id = entry.get("project_id") or "(no project)"
        by_project[project_id] = by_project.get(project_id, 0.0) + float(entry["hours"])
    lines = ["🧾 *Unbilled time*", ""]
    for project_id, hrs in by_project.items():
        lines.append(f"• {project_id[:8]}: {hrs}h")
    if not entries:
        lines.append("(nothing unbilled)")
    if value_resp.status_code == 200:
        body = value_resp.json()
        lines.append("")
        lines.append(f"_Unbilled value:_ *{body['unbilled_value']} EUR*")
    await reply_md(update, "\n".join(lines))
