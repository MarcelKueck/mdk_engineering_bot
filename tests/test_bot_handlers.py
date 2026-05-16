"""Telegram handler tests — mock Update/Context, assert reply content + auth."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mdk_bot.bot.auth import authorized
from mdk_bot.bot.handlers import start, today


def _user(uid: int = 42) -> SimpleNamespace:
    return SimpleNamespace(id=uid, username="marcel")


def _update_for(text: str, *, user_id: int = 42) -> SimpleNamespace:
    reply = AsyncMock()
    message = SimpleNamespace(text=text, reply_text=reply)
    return SimpleNamespace(
        message=message,
        effective_user=_user(user_id),
    )


def _context(args: list[str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(args=args or [])


async def test_authorized_drops_other_users() -> None:
    invoked = AsyncMock()

    @authorized
    async def handler(update, context):  # type: ignore[no-untyped-def]
        await invoked()

    update = _update_for("/start", user_id=999)
    await handler(update, _context())
    assert not invoked.called


async def test_authorized_passes_through_operator() -> None:
    invoked = AsyncMock()

    @authorized
    async def handler(update, context):  # type: ignore[no-untyped-def]
        await invoked()

    update = _update_for("/start", user_id=42)
    await handler(update, _context())
    assert invoked.called


async def test_start_replies_with_command_list() -> None:
    update = _update_for("/start")
    await start.handle(update, _context())
    update.message.reply_text.assert_called_once()
    text = update.message.reply_text.call_args.args[0]
    assert "/today" in text
    assert "/anchor" in text


async def test_today_handler_uses_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """``/today`` formats the API response into Markdown."""

    class FakeResp:
        status_code = 200

        def __init__(self, payload):  # type: ignore[no-untyped-def]
            self._payload = payload

        def json(self):  # type: ignore[no-untyped-def]
            return self._payload

    from mdk_bot.core.time import today_local

    today_iso = today_local().isoformat()

    class FakeClient:
        async def __aenter__(self):  # type: ignore[no-untyped-def]
            return self

        async def __aexit__(self, *_exc):  # type: ignore[no-untyped-def]
            return None

        async def get(self, path, **_kw):  # type: ignore[no-untyped-def]
            if "obligation-instances" in path:
                return FakeResp(
                    [
                        {
                            "obligation_id": "ustva_quartal",
                            "status": "notified",
                            "due_date": today_iso,
                        }
                    ]
                )
            return FakeResp(
                [
                    {
                        "title": "Write tests",
                        "priority": 1,
                        "status": "todo",
                        "due_date": today_iso,
                    }
                ]
            )

    monkeypatch.setattr("mdk_bot.bot.handlers.today.api_client_ctx", lambda: FakeClient())
    update = _update_for("/today")
    await today.handle(update, _context())
    text = update.message.reply_text.call_args.args[0]
    assert "ustva_quartal" in text
    assert "Write tests" in text
