"""Authorize Telegram messages — drop everything not from the operator."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.config import get_settings
from mdk_bot.shared.logging import get_logger

log = get_logger(__name__)

HandlerFn = Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[Any]]


def authorized(handler: HandlerFn) -> HandlerFn:
    """Decorator that silently drops messages from unauthorized users."""

    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        authorized_id = get_settings().AUTHORIZED_TELEGRAM_USER_ID
        user = update.effective_user
        if user is None or user.id != authorized_id:
            log.info(
                "bot.unauthorized_drop",
                user_id=user.id if user else None,
                username=user.username if user else None,
            )
            return None
        return await handler(update, context)

    return wrapper
