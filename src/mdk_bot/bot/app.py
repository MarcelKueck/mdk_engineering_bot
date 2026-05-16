"""Telegram bot entry point — long-polling mode."""

from __future__ import annotations

from telegram.ext import Application, ApplicationBuilder

from mdk_bot.bot.handlers import register_handlers
from mdk_bot.config import get_settings
from mdk_bot.shared.logging import configure_logging, get_logger

log = get_logger(__name__)


def build_application() -> Application:
    """Construct the :class:`Application` with all handlers registered."""
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")
    application = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).build()
    register_handlers(application)
    return application


def run_bot() -> None:
    """Start the bot in long-polling mode (blocks)."""
    configure_logging()
    settings = get_settings()
    log.info(
        "bot.startup",
        environment=settings.ENVIRONMENT,
        authorized_user=settings.AUTHORIZED_TELEGRAM_USER_ID,
    )
    application = build_application()
    application.run_polling(drop_pending_updates=True)
