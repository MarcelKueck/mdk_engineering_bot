"""Send Telegram messages from any process (bot, scheduler, etc.).

The scheduler does not run a Telegram :class:`Application`, so it can't
reuse the bot's handler dispatch. This module wraps :class:`telegram.Bot`
directly — fire-and-forget, no polling.
"""

from __future__ import annotations

from typing import Final

from telegram import Bot
from telegram.constants import ParseMode

from mdk_bot.capabilities.reminders.engine import Notifier
from mdk_bot.config import get_settings
from mdk_bot.shared.logging import get_logger

log = get_logger(__name__)


class TelegramNotifier:
    """Concrete :class:`Notifier` that posts to the operator's Telegram chat."""

    def __init__(self, *, token: str | None = None, chat_id: int | None = None) -> None:
        settings = get_settings()
        self._token = token or settings.TELEGRAM_BOT_TOKEN
        self._chat_id = chat_id or settings.AUTHORIZED_TELEGRAM_USER_ID
        self._bot: Bot | None = None

    @property
    def bot(self) -> Bot:
        if self._bot is None:
            self._bot = Bot(self._token)
        return self._bot

    async def send(self, text: str) -> int | None:
        if not self._token or not self._chat_id:
            log.warning("bot.notifier.skipped", reason="telegram not configured")
            return None
        try:
            msg = await self.bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
            )
            return msg.message_id
        except Exception as exc:
            log.error("bot.notifier.send_failed", error=str(exc))
            return None


class RecordingNotifier:
    """In-memory :class:`Notifier` used by tests."""

    def __init__(self) -> None:
        self.messages: list[str] = []
        self._next_id = 1000

    async def send(self, text: str) -> int | None:
        self.messages.append(text)
        msg_id = self._next_id
        self._next_id += 1
        return msg_id


SCHEDULER_NOTIFIER: Final = "scheduler-notifier"
