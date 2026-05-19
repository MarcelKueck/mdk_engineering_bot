"""Tests for the VIES capability — engine + PDF generator (mocked HTTP)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.vies.client import VIESError, VIESResult
from mdk_bot.capabilities.vies.engine import _build_pdf, is_enabled, validate_vat
from mdk_bot.config import get_settings
from mdk_bot.core.models import VatValidation
from mdk_bot.core.time import now_utc


@pytest.fixture(autouse=True)
def _vies_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_VIES", "true")
    monkeypatch.setenv("VIES_REQUESTER_VAT_ID", "DE123456789")
    get_settings.cache_clear()
    yield
    for var in ("FEATURE_VIES", "VIES_REQUESTER_VAT_ID"):
        os.environ.pop(var, None)
    get_settings.cache_clear()


def test_disabled_when_flag_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FEATURE_VIES", "false")
    get_settings.cache_clear()
    enabled, reason = is_enabled()
    assert not enabled
    assert "FEATURE_VIES" in reason


def test_pdf_starts_with_magic() -> None:
    pdf = _build_pdf(
        vat_id="DE123",
        requester="DE999",
        result=VIESResult(
            valid=True,
            name_match="1",
            address_match="1",
            consultation_number="ABC123",
            raw="<xml/>",
        ),
        queried_at=now_utc(),
    )
    assert pdf.startswith(b"%PDF-1.")
    assert pdf.endswith(b"%%EOF\n")


async def test_validate_vat_persists_and_writes_pdf(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    fake = VIESResult(
        valid=True,
        name_match="1",
        address_match="2",
        consultation_number="CONS123",
        raw="<xml/>",
    )

    class _Client:
        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *_exc: object) -> None:
            return None

        async def check(self, vat_id: str) -> VIESResult:
            return fake

    monkeypatch.setattr("mdk_bot.capabilities.vies.engine.VIESClient", lambda: _Client())
    validation = await validate_vat(session, "DE111222333", storage_root=tmp_path)
    assert validation.valid is True
    assert validation.consultation_number == "CONS123"
    assert Path(validation.pdf_storage_key).exists()
    rows = (await session.execute(select(VatValidation))).scalars().all()
    assert len(rows) == 1


async def test_validate_vat_raises_when_disabled(
    monkeypatch: pytest.MonkeyPatch, session: AsyncSession
) -> None:
    monkeypatch.setenv("FEATURE_VIES", "false")
    get_settings.cache_clear()
    with pytest.raises(VIESError):
        await validate_vat(session, "DE1")
