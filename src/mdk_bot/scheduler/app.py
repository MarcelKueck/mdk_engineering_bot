"""Scheduler service entrypoint — runs APScheduler in the asyncio loop.

The job store uses Postgres (sync driver) so jobs survive restarts. The
only job today is :func:`daily_check_job`, fired at ``DAILY_CHECK_HOUR``
local time. On startup the catalog is also reloaded from disk so the DB
stays in sync with ``obligations.json``.
"""

from __future__ import annotations

import asyncio
import signal
from typing import Any

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from mdk_bot.config import get_settings
from mdk_bot.scheduler.jobs import daily_check_job, reload_obligations_job
from mdk_bot.shared.logging import configure_logging, get_logger

log = get_logger(__name__)


def build_scheduler() -> AsyncIOScheduler:
    """Construct an :class:`AsyncIOScheduler` backed by Postgres."""
    settings = get_settings()
    jobstores: dict[str, Any] = {
        "default": SQLAlchemyJobStore(url=settings.DATABASE_URL_SYNC),
    }
    scheduler = AsyncIOScheduler(jobstores=jobstores, timezone=settings.TIMEZONE)
    scheduler.add_job(
        daily_check_job,
        trigger=CronTrigger(hour=settings.DAILY_CHECK_HOUR, minute=0),
        id="daily_check",
        replace_existing=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.add_job(
        reload_obligations_job,
        trigger=CronTrigger(hour=settings.DAILY_CHECK_HOUR, minute=55),
        id="reload_obligations",
        replace_existing=True,
        misfire_grace_time=60 * 60,
    )
    return scheduler


async def run_scheduler() -> None:
    """Reload the catalog once, then start APScheduler and idle forever."""
    configure_logging()
    settings = get_settings()
    log.info("scheduler.startup", config=settings.safe_dump())

    try:
        await reload_obligations_job()
    except Exception as exc:
        log.error("scheduler.initial_reload_failed", error=str(exc))

    scheduler = build_scheduler()
    scheduler.start()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)
    log.info("scheduler.running")
    await stop_event.wait()
    log.info("scheduler.shutdown")
    scheduler.shutdown(wait=False)
