"""Liveness/readiness endpoint — checks DB + Redis. Unauthenticated."""

from __future__ import annotations

import redis.asyncio as redis_lib
from fastapi import APIRouter
from sqlalchemy import text

from mdk_bot.config import get_settings
from mdk_bot.core.db import get_engine
from mdk_bot.core.schemas import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthStatus)
async def healthz() -> HealthStatus:
    """Return overall + per-dependency health status."""
    db_status = "ok"
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc.__class__.__name__}"

    redis_status = "ok"
    try:
        r = redis_lib.from_url(get_settings().REDIS_URL)
        ping_result = r.ping()
        if hasattr(ping_result, "__await__"):
            await ping_result
        await r.aclose()
    except Exception as exc:
        redis_status = f"error: {exc.__class__.__name__}"

    overall = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return HealthStatus(status=overall, db=db_status, redis=redis_status)
