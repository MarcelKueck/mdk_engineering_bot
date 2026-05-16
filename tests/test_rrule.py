"""Tests for the RRULE / holiday-shift utilities."""

from __future__ import annotations

from datetime import date

import pytest

from mdk_bot.capabilities.reminders.rrule import (
    is_business_day,
    next_anchor_occurrence,
    next_occurrences,
    normalize_rrule,
    shift_for_holidays,
)


def test_normalize_rrule_translates_quarterly() -> None:
    assert normalize_rrule("FREQ=QUARTERLY;BYMONTH=1,4,7,10") == ("FREQ=YEARLY;BYMONTH=1,4,7,10")


def test_is_business_day_weekend() -> None:
    assert is_business_day(date(2025, 4, 7))  # Mon
    assert not is_business_day(date(2025, 4, 12))  # Sat
    assert not is_business_day(date(2025, 4, 13))  # Sun


def test_holiday_shift_good_friday_2025() -> None:
    # Karfreitag 2025-04-18 -> shift past Easter Monday to Tue Apr 22.
    assert shift_for_holidays(date(2025, 4, 18)) == date(2025, 4, 22)


def test_holiday_shift_bavarian_fronleichnam_2025() -> None:
    # Fronleichnam 2025-06-19 (Thu) -> Fri Jun 20.
    assert shift_for_holidays(date(2025, 6, 19)) == date(2025, 6, 20)


def test_holiday_shift_bavarian_allerheiligen_2025() -> None:
    # Allerheiligen 2025-11-01 (Sat, and BY holiday) -> Mon Nov 3.
    assert shift_for_holidays(date(2025, 11, 1)) == date(2025, 11, 3)


def test_holiday_shift_neujahr_falls_on_wed() -> None:
    # 2025-01-01 (Wed) is Neujahr -> Thu Jan 2.
    assert shift_for_holidays(date(2025, 1, 1)) == date(2025, 1, 2)


def test_next_occurrences_quarterly_ustva() -> None:
    rrule = "FREQ=QUARTERLY;BYMONTH=1,4,7,10;BYMONTHDAY=10"
    got = next_occurrences(rrule, after=date(2025, 1, 1), count=4)
    assert got == [
        date(2025, 1, 10),
        date(2025, 4, 10),
        date(2025, 7, 10),
        date(2025, 10, 10),
    ]


def test_next_occurrences_handles_dst_transition() -> None:
    # DST in Europe/Berlin on 2025-03-30 (Sun); a daily rule shouldn't crash,
    # and Mar 30 (Sun) should be shifted forward to Mon Mar 31.
    rrule = "FREQ=DAILY"
    got = next_occurrences(rrule, after=date(2025, 3, 28), count=5)
    # No crash + monotonic + business-day-only.
    assert all(d.weekday() < 5 for d in got)
    # Mar 31 (Mon) appears multiple times because Sat/Sun shift onto it.
    assert date(2025, 3, 31) in got


def test_next_anchor_occurrence_future_anchor() -> None:
    # Anchor in 2027 from 2026 baseline -> same year.
    assert next_anchor_occurrence(date(2027, 1, 15), after=date(2026, 5, 16)) == date(2027, 1, 15)


def test_next_anchor_occurrence_rolls_to_next_year() -> None:
    # Anchor day passed this year -> roll to next year (with holiday shift).
    got = next_anchor_occurrence(date(2024, 3, 5), after=date(2025, 4, 1))
    assert got == date(2026, 3, 5)


@pytest.mark.parametrize(
    "day",
    [
        date(2025, 12, 25),  # 1. Weihnachtstag
        date(2025, 12, 26),  # 2. Weihnachtstag
        date(2025, 10, 3),  # Tag der Deutschen Einheit
        date(2025, 5, 1),  # Tag der Arbeit
    ],
)
def test_federal_holidays_shift(day: date) -> None:
    assert shift_for_holidays(day) > day
