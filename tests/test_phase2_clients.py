"""Smoke tests for the HTTP clients — transport mocked via httpx.MockTransport."""

from __future__ import annotations

import os

import httpx
import pytest

from mdk_bot.capabilities.lexware.client import LexwareClient, LexwareError
from mdk_bot.capabilities.vies.client import VIESClient, VIESError, _split
from mdk_bot.config import get_settings


def test_vies_split_validates_format() -> None:
    assert _split("DE 123 456 789") == ("DE", "123456789")
    with pytest.raises(VIESError):
        _split("12345")


async def test_vies_client_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIES_REQUESTER_VAT_ID", "DE999999999")
    get_settings.cache_clear()
    try:

        async def handler(request: httpx.Request) -> httpx.Response:
            body = (
                '<?xml version="1.0"?>'
                "<env:Envelope xmlns:env='x'>"
                "<env:Body><valid>true</valid>"
                "<requestIdentifier>CONS-1</requestIdentifier>"
                "<traderNameMatch>1</traderNameMatch>"
                "<traderStreetMatch>2</traderStreetMatch>"
                "</env:Body></env:Envelope>"
            )
            return httpx.Response(200, text=body)

        client = VIESClient()
        async with client:
            client._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
            result = await client.check("DE123456789")
        assert result.valid is True
        assert result.consultation_number == "CONS-1"
    finally:
        os.environ.pop("VIES_REQUESTER_VAT_ID", None)
        get_settings.cache_clear()


async def test_vies_client_raises_when_requester_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIES_REQUESTER_VAT_ID", raising=False)
    get_settings.cache_clear()
    with pytest.raises(VIESError):
        async with VIESClient():
            pass


async def test_lexware_client_paginates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEXWARE_API_KEY", "xxx")
    get_settings.cache_clear()
    try:
        pages = [
            httpx.Response(200, json={"content": [{"id": "a"}], "last": False}),
            httpx.Response(200, json={"content": [{"id": "b"}], "last": True}),
        ]

        async def handler(request: httpx.Request) -> httpx.Response:
            return pages.pop(0)

        client = LexwareClient()
        async with client:
            client._client = httpx.AsyncClient(
                transport=httpx.MockTransport(handler),
                base_url="https://example.test",
            )
            seen = []
            async for item in client.list_contacts():
                seen.append(item["id"])
        assert seen == ["a", "b"]
    finally:
        os.environ.pop("LEXWARE_API_KEY", None)
        get_settings.cache_clear()


async def test_lexware_client_raises_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("LEXWARE_API_KEY", raising=False)
    get_settings.cache_clear()
    with pytest.raises(LexwareError):
        async with LexwareClient():
            pass
