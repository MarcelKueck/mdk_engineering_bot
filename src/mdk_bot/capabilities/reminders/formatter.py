"""Compose the user-facing notification text for an :class:`Obligation`."""

from __future__ import annotations

from datetime import date

from mdk_bot.core.models import Obligation, ObligationInstance


def _mandatory_line(obligation: Obligation) -> str:
    if obligation.mandatory_label:
        return f"⚠️ PFLICHT ({obligation.mandatory_label})"
    if obligation.mandatory:
        return "⚠️ PFLICHT"
    return "📌 Empfohlen"


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
    lines.append(f"⏰ Fällig: `{instance.due_date.isoformat()}`")
    lines.append(f"📁 Kategorie: {obligation.category}")
    lines.append(f"⏱️ Aufwand: ~{obligation.estimated_minutes} Min")
    lines.append("")
    lines.append(f"📋 Was zu tun ist: {obligation.action}")
    lines.append(f"🛠️ {obligation.tool}")
    lines.append("")
    lines.append(_mandatory_line(obligation))
    if obligation.penalty:
        lines.append(f"💸 Strafe bei Versäumnis: {obligation.penalty}")

    if obligation.id == "zm_quartal":
        lines.append("")
        lines.append("Falls keine EU-B2B-Umsätze in diesem Zeitraum: /skip zm_quartal")
    elif obligation.skip_if:
        lines.append("")
        lines.append(f"_Ggf. überspringen: {obligation.skip_if}_")

    lines.append("")
    lines.append(f"Erledigt? `/done {obligation.id}`")
    lines.append(f"Überspringen? `/skip {obligation.id}`")

    return "\n".join(lines)


def format_anchor_missing(obligation: Obligation) -> str:
    """Weekly nudge when an anchor-driven obligation has no anchor set."""
    field = obligation.anchor_date_field or "<unknown>"
    return (
        f"ℹ️ *{obligation.title}* hat kein gesetztes Anker-Datum.\n"
        f"Bitte setze `{field}` per `/anchor {field} YYYY-MM-DD`, "
        f"damit ich rechtzeitig erinnern kann."
    )
