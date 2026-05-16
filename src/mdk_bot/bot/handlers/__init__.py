"""Telegram command handlers — one module per command."""

from __future__ import annotations

from telegram.ext import Application, CommandHandler

from mdk_bot.bot.handlers import (
    adhoc,
    anchors,
    details,
    done,
    listing,
    pause,
    skip,
    start,
    today,
    upcoming,
    week,
)
from mdk_bot.bot.handlers import (
    help as help_handler,
)


def register_handlers(application: Application) -> None:
    """Attach every command handler to the running :class:`Application`."""
    application.add_handler(CommandHandler("start", start.handle))
    application.add_handler(CommandHandler("today", today.handle))
    application.add_handler(CommandHandler("week", week.handle))
    application.add_handler(CommandHandler("upcoming", upcoming.handle))
    application.add_handler(CommandHandler("list", listing.handle))
    application.add_handler(CommandHandler("details", details.handle))
    application.add_handler(CommandHandler("done", done.handle))
    application.add_handler(CommandHandler("skip", skip.handle))
    application.add_handler(CommandHandler("anchor", anchors.set_handler))
    application.add_handler(CommandHandler("anchors", anchors.list_handler))
    application.add_handler(CommandHandler("pause", pause.pause_handler))
    application.add_handler(CommandHandler("resume", pause.resume_handler))
    application.add_handler(CommandHandler("adhoc", adhoc.handle))
    application.add_handler(CommandHandler("help", help_handler.handle))
