"""Core helpers: auth, time, audit."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.core import auth, time
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, AuditLog


def test_session_roundtrip() -> None:
    cookie = auth.issue_session("operator")
    assert auth.verify_session(cookie) == "operator"


def test_session_rejects_tampered_value() -> None:
    assert auth.verify_session("nonsense") is None
    assert auth.verify_session(auth.issue_session() + "garbage") is None


def test_login_token_constant_time() -> None:
    assert auth.check_login_token("test-web-token") is True
    assert auth.check_login_token("wrong") is False


def test_time_local_helpers() -> None:
    n = time.now()
    assert n.tzinfo is not None
    assert time.to_local(n).tzinfo is not None
    assert time.today_local() == time.now().date()


def test_ensure_aware_rejects_naive() -> None:
    with pytest.raises(ValueError):
        time.ensure_aware(datetime(2025, 4, 1))


async def test_audit_record_inserts(session: AsyncSession) -> None:
    await record(
        session,
        actor=AuditActor.SCHEDULER,
        action="test.event",
        entity_type="thing",
        entity_id="abc",
        payload={"foo": "bar"},
    )
    rows = (await session.execute(select(AuditLog))).scalars().all()
    assert len(rows) == 1
    assert rows[0].action == "test.event"
    assert rows[0].payload == {"foo": "bar"}
