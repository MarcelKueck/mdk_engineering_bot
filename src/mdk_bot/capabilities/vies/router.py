"""VIES validation API — list past checks, trigger a new check."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.capabilities.vies.client import VIESError
from mdk_bot.capabilities.vies.engine import is_enabled, validate_vat
from mdk_bot.core.models import VatValidation
from mdk_bot.core.schemas import VatValidationRead

router = APIRouter(prefix="/vies", tags=["vies"], dependencies=[AuthDep])


class CheckRequest(BaseModel):
    vat_id: str


@router.get("/checks", response_model=list[VatValidationRead])
async def list_checks(session: AsyncSession = SessionDep) -> list[VatValidation]:
    rows = (
        (
            await session.execute(
                select(VatValidation).order_by(VatValidation.queried_at.desc()).limit(50)
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


@router.post("/check", response_model=VatValidationRead)
async def check(payload: CheckRequest, session: AsyncSession = SessionDep) -> VatValidation:
    enabled, reason = is_enabled()
    if not enabled:
        raise HTTPException(status_code=400, detail=f"VIES disabled: {reason}")
    try:
        return await validate_vat(session, payload.vat_id)
    except VIESError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
