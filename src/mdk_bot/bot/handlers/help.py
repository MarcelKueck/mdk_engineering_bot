"""``/help`` — same command list as ``/start`` but framed as reference."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import operator_handler, reply_md
from mdk_bot.bot.handlers.start import WELCOME


@operator_handler
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the full command reference."""
    await reply_md(update, WELCOME)
