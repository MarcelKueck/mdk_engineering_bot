"""``/start`` — welcome the operator and list main commands."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import operator_handler, reply_md

WELCOME = """\
👋 *MDK Engineering Bot*

Ich erinnere dich an Steuer- und Admin-Pflichten und helfe bei Tasks & Anchors.

Wichtige Befehle:
• /today — heute fällig
• /week — nächste 7 Tage
• /upcoming N — nächste N Instanzen
• /list [kategorie] — Katalog
• /details <id> — Details zu einer Pflicht
• /done <id> | /skip <id> — Status setzen
• /anchor <feld> <YYYY-MM-DD> — Anker setzen
• /anchors — gesetzte Anker
• /pause [stunden] | /resume — Bot pausieren / fortsetzen
• /adhoc — Ad-hoc-Regeln
• /help — Übersicht
"""


@operator_handler
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the welcome message."""
    await reply_md(update, WELCOME)
