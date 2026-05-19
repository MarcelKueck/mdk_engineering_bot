"""Tests for the Lexware sync engine — HTTP mocked."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.lexware import sync as lexware_sync
from mdk_bot.config import get_settings
from mdk_bot.core.models import Invoice, Organization


@pytest.fixture(autouse=True)
def _lexware_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_LEXWARE_SYNC", "true")
    monkeypatch.setenv("LEXWARE_API_KEY", "fake-key")
    get_settings.cache_clear()
    yield
    for var in ("FEATURE_LEXWARE_SYNC", "LEXWARE_API_KEY"):
        os.environ.pop(var, None)
    get_settings.cache_clear()


def test_is_enabled_skips_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEXWARE_API_KEY", raising=False)
    get_settings.cache_clear()
    enabled, reason = lexware_sync.is_enabled()
    assert not enabled and "LEXWARE_API_KEY" in reason


class _FakeClient:
    """Stand-in for :class:`LexwareClient` used in tests."""

    def __init__(
        self,
        *,
        contacts: list[dict[str, Any]] | None = None,
        invoices: list[dict[str, Any]] | None = None,
    ) -> None:
        self._contacts = contacts or []
        self._invoices = invoices or []

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        return None

    async def list_contacts(self) -> AsyncIterator[dict[str, Any]]:
        for item in self._contacts:
            yield item

    async def list_invoices(self) -> AsyncIterator[dict[str, Any]]:
        for item in self._invoices:
            yield item

    async def list_vouchers(self) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}

    async def list_transactions(self) -> AsyncIterator[dict[str, Any]]:
        if False:
            yield {}


async def test_sync_creates_org_and_invoice(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _FakeClient(
        contacts=[
            {"id": "lex-org-1", "company": {"name": "Acme GmbH"}},
        ],
        invoices=[
            {
                "id": "lex-inv-1",
                "voucherNumber": "2026-001",
                "voucherDate": "2026-05-01T00:00:00Z",
                "dueDate": "2026-06-01T00:00:00Z",
                "totalAmount": "119.00",
                "openAmount": "100.00",
                "currency": "EUR",
                "voucherStatus": "open",
                "contactId": "lex-org-1",
            }
        ],
    )
    monkeypatch.setattr("mdk_bot.capabilities.lexware.sync.LexwareClient", lambda: fake)
    stats = await lexware_sync.run_sync(session)
    assert stats.contacts_created == 1
    assert stats.invoices_created == 1

    orgs = (await session.execute(select(Organization))).scalars().all()
    assert any(o.lexware_id == "lex-org-1" for o in orgs)
    invoices = (await session.execute(select(Invoice))).scalars().all()
    assert any(i.lexware_id == "lex-inv-1" for i in invoices)


async def test_sync_idempotent(session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeClient(
        contacts=[{"id": "lex-org-1", "company": {"name": "Acme"}}],
        invoices=[
            {
                "id": "lex-inv-1",
                "voucherNumber": "X",
                "voucherDate": "2026-05-01T00:00:00Z",
                "dueDate": "2026-06-01T00:00:00Z",
                "totalAmount": "50.00",
                "openAmount": "50.00",
                "currency": "EUR",
                "voucherStatus": "open",
                "contactId": "lex-org-1",
            }
        ],
    )
    monkeypatch.setattr("mdk_bot.capabilities.lexware.sync.LexwareClient", lambda: fake)
    await lexware_sync.run_sync(session)
    stats2 = await lexware_sync.run_sync(session)
    assert stats2.contacts_updated == 1
    assert stats2.invoices_updated == 1
    invoices = (await session.execute(select(Invoice))).scalars().all()
    assert len(invoices) == 1
