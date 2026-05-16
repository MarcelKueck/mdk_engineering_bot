"""RRULE expansion + German/Bavarian holiday-aware business-day shifting.

The catalog uses ``FREQ=QUARTERLY`` which is not part of RFC 5545; the
loader leaves the original string in the database but :func:`normalize_rrule`
rewrites it to ``FREQ=YEARLY;BYMONTH=…`` so :mod:`dateutil.rrule` accepts it.

Anchor-driven obligations (insurance renewal, domain renewal) use
:func:`next_anchor_occurrence` instead of an RRULE expansion.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import Final
from zoneinfo import ZoneInfo

import holidays
from dateutil.rrule import rrulestr

from mdk_bot.core.time import local_tz

_QUARTERLY_RE: Final = re.compile(r"FREQ=QUARTERLY", re.IGNORECASE)


def normalize_rrule(rrule: str) -> str:
    """Rewrite catalog-friendly RRULE strings into a dateutil-parseable form.

    ``FREQ=QUARTERLY;BYMONTH=…`` becomes ``FREQ=YEARLY;BYMONTH=…``. Every
    other RRULE is returned unchanged.
    """
    return _QUARTERLY_RE.sub("FREQ=YEARLY", rrule)


def _bavarian_holidays(years: list[int]) -> holidays.HolidayBase:
    """Return a combined federal + Bavarian holiday calendar."""
    return holidays.country_holidays("DE", subdiv="BY", years=years)


def is_business_day(day: date, calendar: holidays.HolidayBase | None = None) -> bool:
    """True if ``day`` is Mon–Fri and not a Bavarian/federal holiday."""
    if day.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    cal = calendar if calendar is not None else _bavarian_holidays([day.year])
    return day not in cal


def shift_for_holidays(
    candidate: date, calendar: holidays.HolidayBase | None = None
) -> date:
    """Push ``candidate`` forward to the next business day if needed."""
    if calendar is None:
        years = sorted({candidate.year, candidate.year + 1})
        calendar = _bavarian_holidays(years)
    current = candidate
    while not is_business_day(current, calendar):
        current = current + timedelta(days=1)
    return current


def next_occurrences(
    rrule: str,
    *,
    after: date,
    count: int = 1,
    tz: ZoneInfo | None = None,
) -> list[date]:
    """Return the next ``count`` occurrences strictly after ``after`` (holiday-shifted).

    Uses ``after`` as the dtstart anchor at midnight in the configured TZ so
    yearly rules without explicit ``BYMONTH/BYMONTHDAY`` still produce output.
    """
    zone = tz or local_tz()
    normalized = normalize_rrule(rrule)
    dtstart = datetime.combine(date(after.year, 1, 1), time.min, tzinfo=zone)
    rule = rrulestr(normalized, dtstart=dtstart)

    cutoff = datetime.combine(after, time.min, tzinfo=zone)
    years_to_check = sorted({after.year, after.year + 1, after.year + 2})
    calendar = _bavarian_holidays(years_to_check)

    occurrences: list[date] = []
    iterator = rule.xafter(cutoff, count=count * 5, inc=False)
    for occ in iterator:
        shifted = shift_for_holidays(occ.date(), calendar)
        occurrences.append(shifted)
        if len(occurrences) >= count:
            break
    return occurrences


def next_anchor_occurrence(anchor: date, *, after: date) -> date:
    """Return the next yearly recurrence of ``anchor``'s month/day strictly after ``after``.

    Used by obligations like ``berufshaftpflicht_verlaengerung`` whose due
    date is derived from a user-supplied expiry/anchor date.
    """
    candidate = date(after.year, anchor.month, anchor.day)
    if candidate <= after:
        candidate = date(after.year + 1, anchor.month, anchor.day)
    return shift_for_holidays(candidate)
