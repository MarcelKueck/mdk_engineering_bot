"""``/start`` — welcome the operator and list main commands."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import operator_handler, reply_md

WELCOME = """\
👋 *MDK Engineering Bot*

I remind you about tax and admin obligations and help with tasks & anchors.

Main commands:
• /today — due today
• /week — next 7 days
• /upcoming N — next N instances
• /list [category] — catalog
• /details <id> — show details for an obligation
• /done <id> | /skip <id> — set status
• /anchor <field> <YYYY-MM-DD> — set an anchor date
• /anchors — list anchor dates
• /pause [hours] | /resume — pause/resume the bot
• /adhoc — ad-hoc rules
• /help — show this help
"""


@operator_handler
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the welcome message."""
    await reply_md(update, WELCOME)
