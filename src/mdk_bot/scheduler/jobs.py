"""Job functions invoked by APScheduler.

Each job acquires its own DB session via :func:`session_scope` so jobs
can be triggered manually (e.g. from tests or an admin endpoint).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from mdk_bot.bot.notifier import TelegramNotifier
from mdk_bot.capabilities.reminders.engine import run_daily_check
from mdk_bot.capabilities.reminders.loader import load_obligations_from_file
from mdk_bot.config import get_settings
from mdk_bot.core.db import session_scope
from mdk_bot.shared.logging import get_logger

log = get_logger(__name__)


async def daily_check_job(today: date | None = None) -> None:
    """Run the reminder engine. ``today`` lets tests pin the clock."""
    notifier = TelegramNotifier()
    async with session_scope() as session:
        stats = await run_daily_check(session, notifier, today=today)
    log.info("scheduler.daily_check.done", **stats)


async def reload_obligations_job() -> None:
    """Re-read ``obligations.json`` and upsert into the database."""
    settings = get_settings()
    async with session_scope() as session:
        n, m = await load_obligations_from_file(session, Path(settings.OBLIGATIONS_FILE))
    log.info("scheduler.reload_obligations.done", obligations=n, adhoc_rules=m)
