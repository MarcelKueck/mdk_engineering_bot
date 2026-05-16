"""HTTP client used by the bot (and other services) to call the Core API.

We don't talk to the database from the Telegram bot — every command goes
through ``/api/v1/*`` with an internal service token. This keeps the API
as the single domain layer and makes the bot easy to test.
"""

from __future__ import annotations

from typing import Any

import httpx

from mdk_bot.config import get_settings


class APIClient:
    """Thin async wrapper around :class:`httpx.AsyncClient`."""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.INTERNAL_API_URL).rstrip("/")
        self._token = token or settings.INTERNAL_API_TOKEN
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> APIClient:
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={"X-Internal-Token": self._token},
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
            raise RuntimeError("APIClient used outside its async context manager.")
        return self._client

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.client.get(path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.client.post(path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.client.put(path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self.client.delete(path, **kwargs)
