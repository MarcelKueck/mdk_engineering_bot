"""Compose the user-facing notification text for an :class:`Obligation`."""

from __future__ import annotations

from datetime import date

from mdk_bot.core.models import Obligation, ObligationInstance


def _mandatory_line(obligation: Obligation) -> str:
    if obligation.mandatory_label:
        return f"⚠️ MANDATORY ({obligation.mandatory_label})"
    if obligation.mandatory:
        return "⚠️ MANDATORY"
    return "📌 Recommended"


def format_notification(
    obligation: Obligation, instance: ObligationInstance, *, today: date | None = None
) -> str:
    """Return a Telegram-Markdown ready message for ``instance``.

    Conditional notes are appended where the obligation declares
    ``skip_if`` or a category-specific reminder (e.g. ZM).
    """
    lines: list[str] = []
    lines.append(f"🔔 *{obligation.title}*")
    lines.append("")
    lines.append(f"⏰ Due: `{instance.due_date.isoformat()}`")
    lines.append(f"📁 Category: {obligation.category}")
    lines.append(f"⏱️ Effort: ~{obligation.estimated_minutes} min")
    lines.append("")
    lines.append(f"📋 What to do: {obligation.action}")
    lines.append(f"🛠️ {obligation.tool}")
    lines.append("")
    lines.append(_mandatory_line(obligation))
    if obligation.penalty:
        lines.append(f"💸 Penalty if missed: {obligation.penalty}")

    if obligation.id == "zm_quartal":
        lines.append("")
        lines.append("If no EU B2B sales this period: /skip zm_quartal")
    elif obligation.skip_if:
        lines.append("")
        lines.append(f"_May be skipped: {obligation.skip_if}_")

    lines.append("")
    lines.append(f"Done? `/done {obligation.id}`")
    lines.append(f"Skip? `/skip {obligation.id}`")

    return "\n".join(lines)


def format_anchor_missing(obligation: Obligation) -> str:
    """Weekly nudge when an anchor-driven obligation has no anchor set."""
    field = obligation.anchor_date_field or "<unknown>"
    return (
        f"ℹ️ *{obligation.title}* has no anchor date set.\n"
        f"Please set `{field}` via `/anchor {field} YYYY-MM-DD` "
        f"so I can remind you in time."
    )
