"""Timezone-aware datetime helpers.

All datetimes in the system must be timezone-aware. Naive datetimes are
treated as a bug. Use :func:`now` and :func:`today_local` instead of
:func:`datetime.now` / :func:`date.today`.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from mdk_bot.config import get_settings


def local_tz() -> ZoneInfo:
    """Return the configured local timezone (Europe/Berlin by default)."""
    return ZoneInfo(get_settings().TIMEZONE)


def now(tz: ZoneInfo | None = None) -> datetime:
    """Return current tz-aware datetime in ``tz`` (defaults to configured TZ)."""
    return datetime.now(tz or local_tz())


def now_utc() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


def today_local() -> date:
    """Return today's date in the configured local timezone."""
    return now().date()


def to_local(dt: datetime) -> datetime:
    """Convert ``dt`` (must be tz-aware) to the configured local timezone."""
    if dt.tzinfo is None:
        raise ValueError("Naive datetime passed to to_local()")
    return dt.astimezone(local_tz())


def ensure_aware(dt: datetime) -> datetime:
    """Raise if ``dt`` is naive; otherwise return ``dt`` unchanged."""
    if dt.tzinfo is None:
        raise ValueError(f"Naive datetime not allowed: {dt!r}")
    return dt
