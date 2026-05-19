"""Read-only API for the Lexware-synced finance data + a manual sync trigger."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.capabilities.lexware import sync as lexware_sync
from mdk_bot.core.models import AuditLog, Invoice, InvoiceStatus, Receipt
from mdk_bot.core.schemas import InvoiceRead, ReceiptRead

router = APIRouter(prefix="/finance", tags=["finance"], dependencies=[AuthDep])


@router.get("/invoices", response_model=list[InvoiceRead])
async def list_invoices(
    session: AsyncSession = SessionDep, status_filter: InvoiceStatus | None = None
) -> list[Invoice]:
    stmt = select(Invoice).order_by(Invoice.issue_date.desc().nulls_last())
    if status_filter is not None:
        stmt = stmt.where(Invoice.status == status_filter)
    rows = (await session.execute(stmt)).scalars().all()
    return list(rows)


@router.get("/receipts", response_model=list[ReceiptRead])
async def list_receipts(session: AsyncSession = SessionDep) -> list[Receipt]:
    rows = (
        (await session.execute(select(Receipt).order_by(Receipt.date.desc().nulls_last())))
        .scalars()
        .all()
    )
    return list(rows)


@router.get("/summary")
async def finance_summary(session: AsyncSession = SessionDep) -> dict[str, object]:
    """Aggregate figures used by ``/finance`` in Telegram + dashboard."""
    open_count = await session.scalar(
        select(func.count())
        .select_from(Invoice)
        .where(Invoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.OVERDUE]))
    )
    open_total = await session.scalar(
        select(func.coalesce(func.sum(Invoice.total_gross), 0)).where(
            Invoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.OVERDUE])
        )
    )
    overdue_count = await session.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.status == InvoiceStatus.OVERDUE)
    )
    last_sync_row = await session.execute(
        select(AuditLog.created_at)
        .where(AuditLog.action == "lexware.sync.completed")
        .order_by(AuditLog.created_at.desc())
        .limit(1)
    )
    last_sync = last_sync_row.scalar_one_or_none()
    enabled, reason = lexware_sync.is_enabled()
    return {
        "lexware_enabled": enabled,
        "lexware_disabled_reason": reason,
        "open_invoice_count": int(open_count or 0),
        "open_invoice_total": float(open_total or 0),
        "overdue_invoice_count": int(overdue_count or 0),
        "last_sync_at": last_sync.isoformat() if last_sync else None,
    }


@router.post("/sync")
async def trigger_sync(session: AsyncSession = SessionDep) -> dict[str, int]:
    """Manually trigger a Lexware sync (used by ``/sync_now`` in Telegram)."""
    enabled, reason = lexware_sync.is_enabled()
    if not enabled:
        raise HTTPException(status_code=400, detail=f"Lexware disabled: {reason}")
    stats = await lexware_sync.run_sync(session)
    return stats.to_dict()


@router.get("/stale")
async def stale_sync(session: AsyncSession = SessionDep) -> dict[str, object]:
    """Helper for monitoring: is the last sync older than 26h?"""
    last_sync = await session.scalar(
        select(func.max(AuditLog.created_at)).where(AuditLog.action == "lexware.sync.completed")
    )
    if last_sync is None:
        return {"stale": True, "last_sync_at": None}
    now = datetime.now(last_sync.tzinfo) if last_sync.tzinfo else datetime.utcnow()
    return {
        "stale": (now - last_sync) > timedelta(hours=26),
        "last_sync_at": last_sync.isoformat(),
    }
