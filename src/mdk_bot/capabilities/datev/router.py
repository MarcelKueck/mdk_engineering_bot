"""DATEV export API — trigger an on-demand export for a given year."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.capabilities.datev.exporter import export_year, is_enabled

router = APIRouter(prefix="/datev", tags=["datev"], dependencies=[AuthDep])


@router.post("/export/{year}")
async def export(year: int, session: AsyncSession = SessionDep) -> dict[str, object]:
    enabled, reason = is_enabled()
    if not enabled:
        raise HTTPException(status_code=400, detail=f"DATEV disabled: {reason}")
    result = await export_year(session, year)
    return {
        "csv_path": str(result.csv_path),
        "metadata_path": str(result.metadata_path),
        "invoice_count": result.invoice_count,
        "receipt_count": result.receipt_count,
    }
