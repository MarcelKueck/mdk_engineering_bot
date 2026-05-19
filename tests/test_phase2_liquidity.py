"""Tests for the liquidity engine."""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.liquidity.engine import (
    _project_until,
    compute_snapshot,
    is_enabled,
)
from mdk_bot.config import get_settings


@pytest.fixture(autouse=True)
def _liquidity_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_LIQUIDITY", "true")
    monkeypatch.setenv("LIQUIDITY_OPENING_BALANCE", "5000")
    monkeypatch.setenv("STEUERRUECKLAGE_RATE", "0.30")
    get_settings.cache_clear()
    yield
    for var in ("FEATURE_LIQUIDITY", "LIQUIDITY_OPENING_BALANCE", "STEUERRUECKLAGE_RATE"):
        os.environ.pop(var, None)
    get_settings.cache_clear()


def test_is_enabled_requires_flag_and_balance(monkeypatch: pytest.MonkeyPatch) -> None:
    enabled, _ = is_enabled()
    assert enabled

    monkeypatch.setenv("FEATURE_LIQUIDITY", "false")
    get_settings.cache_clear()
    enabled, reason = is_enabled()
    assert not enabled and "FEATURE_LIQUIDITY" in reason


def test_project_until_returns_none_when_solvent() -> None:
    result = _project_until(
        opening_balance=Decimal("10000"),
        monthly_burn=Decimal("100"),
        steuerrate=Decimal("0"),
        expected_inflows=[],
        as_of=date(2026, 5, 19),
        horizon_days=60,
    )
    assert result is None


def test_project_until_finds_runway_when_burning() -> None:
    result = _project_until(
        opening_balance=Decimal("250"),
        monthly_burn=Decimal("200"),
        steuerrate=Decimal("0"),
        expected_inflows=[],
        as_of=date(2026, 1, 1),
        horizon_days=120,
    )
    # 250 - 200 at end of Jan = 50. End of Feb: 50 - 200 = -150. The negative
    # is detected on March 1 (next iteration's balance check).
    assert result is not None
    assert result == date(2026, 3, 1)


async def test_compute_snapshot_runs(session: AsyncSession) -> None:
    comp = await compute_snapshot(session, as_of=date(2026, 5, 19))
    assert comp.opening_balance == Decimal("5000")
    assert isinstance(comp.scheduled_outflows, list)
