"""Telegram command handlers — one module per command."""

from __future__ import annotations

from telegram.ext import Application, CommandHandler

from mdk_bot.bot.handlers import (
    adhoc,
    anchors,
    datev,
    details,
    done,
    dunning,
    expenses,
    finance,
    listing,
    pause,
    runway,
    skip,
    start,
    time_tracking,
    today,
    upcoming,
    ustva,
    vat,
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
    # ---- Phase 2 finance commands ----------------------------------------
    application.add_handler(CommandHandler("finance", finance.finance))
    application.add_handler(CommandHandler("sync_now", finance.sync_now))
    application.add_handler(CommandHandler("expenses", expenses.list_expenses))
    application.add_handler(CommandHandler("expense_add", expenses.add_expense))
    application.add_handler(CommandHandler("expense_edit", expenses.edit_expense))
    application.add_handler(CommandHandler("expense_rm", expenses.rm_expense))
    application.add_handler(CommandHandler("log", time_tracking.log))
    application.add_handler(CommandHandler("hours", time_tracking.hours))
    application.add_handler(CommandHandler("unbilled", time_tracking.unbilled))
    application.add_handler(CommandHandler("ustva", ustva.show))
    application.add_handler(CommandHandler("approve_ustva", ustva.approve))
    application.add_handler(CommandHandler("runway", runway.show))
    application.add_handler(CommandHandler("liquidity", runway.show))
    application.add_handler(CommandHandler("send_mahnung", dunning.send_mahnung))
    application.add_handler(CommandHandler("vat", vat.check))
    application.add_handler(CommandHandler("datev_export", datev.export))
