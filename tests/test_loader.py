"""Loader: JSON parsing + idempotent upsert."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.reminders.loader import load_obligations_from_file
from mdk_bot.core.models import AdhocRules, Obligation


@pytest.fixture
def catalog_path(tmp_path: Path) -> Path:
    payload = {
        "obligations": [
            {
                "id": "ustva_quartal",
                "title": "USt-Voranmeldung Quartal",
                "category": "steuer",
                "recurrence": "FREQ=QUARTERLY;BYMONTH=1,4,7,10;BYMONTHDAY=10",
                "lead_time_days": 7,
                "action": "An ELSTER senden",
                "tool": "Lexware → ELSTER",
                "mandatory": True,
                "estimated_minutes": 15,
                "penalty": "10%",
            },
            {
                "id": "zm_quartal",
                "title": "ZM Quartal",
                "category": "steuer",
                "recurrence": "FREQ=QUARTERLY;BYMONTH=1,4,7,10;BYMONTHDAY=25",
                "lead_time_days": 5,
                "action": "ZM-Formular eintragen",
                "tool": "ELSTER",
                "mandatory": "bei EU-B2B-Umsätzen",
                "estimated_minutes": 10,
                "skip_if": "keine EU-B2B-Umsätze",
            },
        ],
        "ad_hoc_rules": [
            {"id": "eu_kunde_vies_check", "title": "VIES", "trigger": "...", "action": "..."}
        ],
    }
    path = tmp_path / "obligations.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


async def test_loader_inserts_obligations(session: AsyncSession, catalog_path: Path) -> None:
    n, m = await load_obligations_from_file(session, catalog_path)
    await session.commit()
    assert n == 2
    assert m == 1
    rows = (await session.execute(select(Obligation))).scalars().all()
    assert {r.id for r in rows} == {"ustva_quartal", "zm_quartal"}
    zm = next(r for r in rows if r.id == "zm_quartal")
    # Conditional-mandatory string becomes True + a label.
    assert zm.mandatory is True
    assert zm.mandatory_label == "bei EU-B2B-Umsätzen"


async def test_loader_is_idempotent(session: AsyncSession, catalog_path: Path) -> None:
    await load_obligations_from_file(session, catalog_path)
    await session.commit()
    await load_obligations_from_file(session, catalog_path)
    await session.commit()
    rows = (await session.execute(select(Obligation))).scalars().all()
    assert len(rows) == 2


async def test_loader_stores_adhoc_payload(session: AsyncSession, catalog_path: Path) -> None:
    await load_obligations_from_file(session, catalog_path)
    await session.commit()
    adhoc = await session.get(AdhocRules, 1)
    assert adhoc is not None
    assert len(adhoc.payload) == 1
    assert adhoc.payload[0]["id"] == "eu_kunde_vies_check"


async def test_loader_loads_real_catalog(session: AsyncSession) -> None:
    """The shipped obligations.json must parse cleanly."""
    repo_root = Path(__file__).resolve().parent.parent
    n, m = await load_obligations_from_file(session, repo_root / "obligations.json")
    await session.commit()
    assert n == 15
    assert m == 6
