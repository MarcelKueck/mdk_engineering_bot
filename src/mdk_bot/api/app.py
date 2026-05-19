"""FastAPI application factory.

The app exposes:
- ``/healthz`` — unauthenticated liveness/readiness check
- ``/login``, ``/logout`` — session-cookie endpoints
- ``/api/v1/*`` — JSON CRUD/business endpoints (session or internal token)
- ``/web/*`` — HTMX-driven minimal admin UI (session-cookie only)
"""

from __future__ import annotations

import asyncio
import traceback
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from mdk_bot import __version__
from mdk_bot.api.routers import (
    anchors,
    audit,
    health,
    obligations,
    organizations,
    persons,
    projects,
    tasks,
)
from mdk_bot.capabilities.datev.router import router as datev_router
from mdk_bot.capabilities.dunning.router import router as dunning_router
from mdk_bot.capabilities.expenses.router import router as expenses_router
from mdk_bot.capabilities.lexware.router import router as lexware_router
from mdk_bot.capabilities.liquidity.router import router as liquidity_router
from mdk_bot.capabilities.timetracking.router import router as time_router
from mdk_bot.capabilities.ustva.router import router as ustva_router
from mdk_bot.capabilities.vies.router import router as vies_router
from mdk_bot.config import get_settings
from mdk_bot.core.db import get_engine, reset_engine
from mdk_bot.shared.logging import configure_logging, get_logger
from mdk_bot.web import views as web_views
from mdk_bot.web.assets import STATIC_DIR

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """App lifespan — ensure the engine is up and tear it down at shutdown."""
    settings = get_settings()
    configure_logging()
    log.info(
        "api.startup",
        version=__version__,
        environment=settings.ENVIRONMENT,
        config=settings.safe_dump(),
    )
    # Trigger lazy engine construction so failures surface at startup.
    # Retry a few times so a slow Docker DNS resolution or a Postgres
    # container that is still starting does not produce a spurious warning.
    engine = get_engine()
    last_exc: Exception | None = None
    for attempt in range(5):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            last_exc = None
            break
        except Exception as exc:  # pragma: no cover - integration only
            last_exc = exc
            await asyncio.sleep(1.0 + attempt)
    if last_exc is not None:  # pragma: no cover - integration only
        log.warning("api.db_unreachable_at_startup", error=str(last_exc))

    yield

    await reset_engine()
    log.info("api.shutdown")


def create_app() -> FastAPI:
    """Application factory — separate from module import for testability."""
    app = FastAPI(
        title="MDK Engineering Bot",
        version=__version__,
        docs_url="/api/v1/docs",
        openapi_url="/api/v1/openapi.json",
        lifespan=lifespan,
    )

    app.include_router(health.router)
    app.include_router(web_views.router)

    api = FastAPI(title="MDK API", version=__version__)
    api.include_router(persons.router)
    api.include_router(organizations.router)
    api.include_router(projects.router)
    api.include_router(tasks.router)
    api.include_router(obligations.router)
    api.include_router(obligations.instances_router)
    api.include_router(obligations.pause_router)
    api.include_router(anchors.router)
    api.include_router(audit.router)
    api.include_router(lexware_router)
    api.include_router(expenses_router)
    api.include_router(time_router)
    api.include_router(ustva_router)
    api.include_router(liquidity_router)
    api.include_router(dunning_router)
    api.include_router(vies_router)
    api.include_router(datev_router)
    app.mount("/api/v1", api)

    if STATIC_DIR.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(STATIC_DIR)),
            name="static",
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.error(
            "api.unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(status_code=500, content={"detail": "internal error"})

    return app


app = create_app()
