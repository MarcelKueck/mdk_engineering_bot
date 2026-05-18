"""API surface for obligations + obligation instances."""

from __future__ import annotations

from datetime import date

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from mdk_bot.core.models import ObligationInstance
from tests.factories import make_obligation


async def _seed_obligation(sessionmaker_: async_sessionmaker[AsyncSession]) -> None:
    async with sessionmaker_() as session:
        session.add(make_obligation())
        await session.commit()


async def test_obligations_list_and_get(
    client: AsyncClient, sessionmaker_: async_sessionmaker[AsyncSession]
) -> None:
    await _seed_obligation(sessionmaker_)
    resp = await client.get("/api/v1/obligations")
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == "ustva_quartal"

    resp = await client.get("/api/v1/obligations/ustva_quartal")
    assert resp.status_code == 200
    assert resp.json()["title"] == "USt-Voranmeldung Quartal"


async def test_instance_done_transition(
    client: AsyncClient, sessionmaker_: async_sessionmaker[AsyncSession]
) -> None:
    await _seed_obligation(sessionmaker_)
    async with sessionmaker_() as session:
        instance = ObligationInstance(obligation_id="ustva_quartal", due_date=date(2025, 4, 10))
        session.add(instance)
        await session.commit()
        instance_id = str(instance.id)

    resp = await client.post(f"/api/v1/obligation-instances/{instance_id}/done")
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"


async def test_upcoming_filters_by_days(
    client: AsyncClient, sessionmaker_: async_sessionmaker[AsyncSession]
) -> None:
    await _seed_obligation(sessionmaker_)
    async with sessionmaker_() as session:
        session.add(ObligationInstance(obligation_id="ustva_quartal", due_date=date(2099, 1, 1)))
        await session.commit()
    resp = await client.get("/api/v1/obligation-instances/upcoming?days=7")
    assert resp.status_code == 200
    assert resp.json() == []
