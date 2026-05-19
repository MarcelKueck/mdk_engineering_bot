"""Async HTTP client for the Lexware Office (lexoffice) REST API.

Public docs: https://developers.lexoffice.io/docs/. Auth is a bearer
token. The client paginates the voucherlist endpoint and respects rate
limits with exponential backoff via ``tenacity``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from mdk_bot.config import get_settings
from mdk_bot.shared.logging import get_logger

log = get_logger(__name__)


class LexwareError(RuntimeError):
    """Any non-recoverable error from the Lexware API."""


class LexwareClient:
    """Thin wrapper around ``httpx.AsyncClient`` for lexoffice endpoints."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.LEXWARE_API_KEY
        self._base_url = (base_url or settings.LEXWARE_API_BASE_URL).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> LexwareClient:
        if not self._api_key:
            raise LexwareError("LEXWARE_API_KEY is not configured.")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(30.0, connect=10.0),
        )
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("LexwareClient used outside its async context.")
        return self._client

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Send a request with retry on 429 / 5xx and transport errors."""

        async def _do() -> httpx.Response:
            response = await self.client.request(method, path, **kwargs)
            if response.status_code in (429, 502, 503, 504):
                response.raise_for_status()
            return response

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=1, max=30),
            retry=retry_if_exception_type((httpx.HTTPError,)),
            reraise=True,
        ):
            with attempt:
                response = await _do()
        return response

    async def list_contacts(self) -> AsyncIterator[dict[str, Any]]:
        """Yield every contact, transparently following pagination."""
        async for page in self._paginate("/contacts"):
            for item in page.get("content", []):
                yield item

    async def list_invoices(self) -> AsyncIterator[dict[str, Any]]:
        """Yield every invoice voucher (status filter `paid|open|overdue`)."""
        async for page in self._paginate(
            "/voucherlist",
            params={
                "voucherType": "invoice",
                "voucherStatus": "open,paid,overdue,draft",
            },
        ):
            for item in page.get("content", []):
                yield item

    async def list_vouchers(self) -> AsyncIterator[dict[str, Any]]:
        """Yield every receipt voucher (expense type)."""
        async for page in self._paginate(
            "/voucherlist",
            params={
                "voucherType": "purchaseinvoice,purchasecreditnote",
                "voucherStatus": "open,paid,overdue,draft",
            },
        ):
            for item in page.get("content", []):
                yield item

    async def list_transactions(self) -> AsyncIterator[dict[str, Any]]:
        """Yield bank transactions if exposed (lexoffice may 404 — handled)."""
        try:
            async for page in self._paginate("/transactions"):
                for item in page.get("content", []):
                    yield item
        except LexwareError:
            log.info("lexware.transactions.unavailable")

    async def get_invoice(self, lexware_id: str) -> dict[str, Any]:
        """Fetch the full invoice detail for ``lexware_id``."""
        response = await self._request("GET", f"/invoices/{lexware_id}")
        if response.status_code != 200:
            raise LexwareError(f"GET /invoices/{lexware_id} returned {response.status_code}")
        return response.json()  # type: ignore[no-any-return]

    async def _paginate(
        self, path: str, *, params: dict[str, str] | None = None
    ) -> AsyncIterator[dict[str, Any]]:
        page = 0
        size = 100
        while True:
            page_params: dict[str, str] = {"page": str(page), "size": str(size)}
            if params:
                page_params.update(params)
            response = await self._request("GET", path, params=page_params)
            if response.status_code == 404:
                raise LexwareError(f"GET {path} returned 404")
            if response.status_code >= 400:
                raise LexwareError(
                    f"GET {path} returned {response.status_code}: {response.text[:200]}"
                )
            body = response.json()
            yield body
            if body.get("last", True):
                return
            page += 1
