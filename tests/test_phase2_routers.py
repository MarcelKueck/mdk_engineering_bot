"""End-to-end router tests for the Phase 2 capabilities."""

from __future__ import annotations

import os
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from mdk_bot.config import get_settings
from mdk_bot.core.models import Invoice, InvoiceStatus


async def test_finance_summary_when_lexware_disabled(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/finance/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["lexware_enabled"] is False


async def test_finance_sync_rejected_when_disabled(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/finance/sync")
    assert resp.status_code == 400


async def test_ustva_prepare_and_approve(client: AsyncClient) -> None:
    prep = await client.post("/api/v1/ustva/prepare")
    assert prep.status_code == 200, prep.text
    period = prep.json()
    approve = await client.post(f"/api/v1/ustva/{period['id']}/approve")
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"


async def test_dunning_prepare_then_send(
    client: AsyncClient, sessionmaker_: async_sessionmaker
) -> None:
    today = date(2026, 5, 19)
    async with sessionmaker_() as s:
        s.add(
            Invoice(
                number="2026-XXX",
                issue_date=today - timedelta(days=20),
                due_date=today - timedelta(days=14),
                total_gross=200.0,
                status=InvoiceStatus.OPEN,
            )
        )
        await s.commit()
    prep = await client.post("/api/v1/dunning/prepare")
    assert prep.status_code == 200
    drafted = prep.json()["drafted"]
    assert drafted >= 1

    runs = await client.get("/api/v1/dunning/runs")
    assert runs.status_code == 200
    run_id = runs.json()[0]["id"]
    send = await client.post(f"/api/v1/dunning/{run_id}/send")
    assert send.status_code == 200
    assert send.json()["sent_at"] is not None


@pytest.fixture
def _datev_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("FEATURE_DATEV", "true")
    monkeypatch.setenv("DATEV_EXPORT_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield
    for var in ("FEATURE_DATEV", "DATEV_EXPORT_DIR"):
        os.environ.pop(var, None)
    get_settings.cache_clear()


async def test_datev_export_via_api(client: AsyncClient, _datev_env: None) -> None:
    resp = await client.post("/api/v1/datev/export/2025")
    assert resp.status_code == 200
    body = resp.json()
    assert "csv_path" in body
    assert body["invoice_count"] == 0


async def test_vies_disabled_returns_400(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/vies/check", json={"vat_id": "DE1"})
    assert resp.status_code == 400


async def test_liquidity_current_disabled(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/liquidity/current")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False
