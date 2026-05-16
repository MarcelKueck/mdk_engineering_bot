"""Shared helpers for command handlers — APIClient construction, error reply."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any

import httpx
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from mdk_bot.bot.auth import authorized
from mdk_bot.shared.api_client import APIClient
from mdk_bot.shared.logging import get_logger

log = get_logger(__name__)


def with_error_reply(handler: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """Wrap a handler so unhandled exceptions don't crash the bot."""

    @wraps(handler)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        try:
            return await handler(update, context)
        except Exception as exc:
            log.error(
                "bot.handler.error",
                handler=handler.__name__,
                error=str(exc),
                exc_info=True,
            )
            if update.message is not None:
                await update.message.reply_text(
                    "Etwas ist schiefgegangen. Schau in die Logs."
                )
            return None

    return wrapper


def operator_handler(handler: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
    """Combine the authorized + error-reply wrappers."""
    return authorized(with_error_reply(handler))


async def api() -> APIClient:
    """Return an APIClient inside an entered async context.

    Callers must use ``async with api_client_ctx()`` instead — kept here as
    a documentation anchor.
    """
    raise NotImplementedError("use api_client_ctx() in an async with block")


def api_client_ctx() -> APIClient:
    """Return an :class:`APIClient` ready to be used as ``async with``."""
    return APIClient()


async def reply_md(update: Update, text: str) -> None:
    """Reply with Markdown formatting."""
    if update.message is not None:
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


async def reply(update: Update, text: str) -> None:
    """Reply with plain text."""
    if update.message is not None:
        await update.message.reply_text(text)


def fmt_http_error(response: httpx.Response) -> str:
    """Render an HTTP error as a short, user-facing string."""
    try:
        body = response.json()
        detail = body.get("detail", "")
    except Exception:
        detail = response.text[:200]
    return f"API-Fehler {response.status_code}: {detail}"
