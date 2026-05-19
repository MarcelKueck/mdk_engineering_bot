"""Job functions invoked by APScheduler.

Each job acquires its own DB session via :func:`session_scope` so jobs
can be triggered manually (e.g. from tests or an admin endpoint).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from mdk_bot.bot.notifier import TelegramNotifier
from mdk_bot.capabilities.datev import exporter as datev_exporter
from mdk_bot.capabilities.dunning import engine as dunning_engine
from mdk_bot.capabilities.lexware import sync as lexware_sync
from mdk_bot.capabilities.liquidity import engine as liquidity_engine
from mdk_bot.capabilities.reminders.engine import run_daily_check
from mdk_bot.capabilities.reminders.loader import load_obligations_from_file
from mdk_bot.capabilities.ustva import engine as ustva_engine
from mdk_bot.config import get_settings
from mdk_bot.core.audit import record
from mdk_bot.core.db import session_scope
from mdk_bot.core.models import (
    AuditActor,
    DunningRun,
    LiquiditySnapshot,
    UstvaPeriod,
    UstvaStatus,
)
from mdk_bot.core.time import now_utc, today_local
from mdk_bot.shared.logging import get_logger

log = get_logger(__name__)


async def daily_check_job(today: date | None = None) -> None:
    """Run the reminder engine. ``today`` lets tests pin the clock."""
    notifier = TelegramNotifier()
    async with session_scope() as session:
        stats = await run_daily_check(session, notifier, today=today)
    log.info("scheduler.daily_check.done", **stats)


async def reload_obligations_job() -> None:
    """Re-read ``obligations.json`` and upsert into the database."""
    settings = get_settings()
    async with session_scope() as session:
        n, m = await load_obligations_from_file(session, Path(settings.OBLIGATIONS_FILE))
    log.info("scheduler.reload_obligations.done", obligations=n, adhoc_rules=m)


async def lexware_sync_job() -> None:
    """Daily Lexware Office pull (07:00 Europe/Berlin)."""
    enabled, reason = lexware_sync.is_enabled()
    if not enabled:
        log.info("scheduler.lexware_sync.skipped", reason=reason)
        return
    async with session_scope() as session:
        stats = await lexware_sync.run_sync(session)
    log.info("scheduler.lexware_sync.done", **stats.to_dict())


async def ustva_preview_job(today: date | None = None) -> None:
    """Prepare a UStVA preview around quarter-end and notify the operator."""
    enabled, reason = ustva_engine.is_enabled()
    if not enabled:
        log.info("scheduler.ustva.skipped", reason=reason)
        return
    today = today or today_local()
    if not ustva_engine.is_in_preview_window(today, lead_days=7):
        return
    year, quarter, period_start, period_end = ustva_engine.current_quarter(today)
    notifier = TelegramNotifier()
    async with session_scope() as session:
        stmt = (
            select(UstvaPeriod)
            .where(UstvaPeriod.year == year)
            .where(UstvaPeriod.quarter == quarter)
        )
        period = (await session.execute(stmt)).scalar_one_or_none()
        if period is None:
            period = UstvaPeriod(
                year=year,
                quarter=quarter,
                period_start=period_start,
                period_end=period_end,
                status=UstvaStatus.REVIEW,
            )
            session.add(period)
        payload = await ustva_engine.compute_payload(
            session, period_start=period_start, period_end=period_end
        )
        gaps = await ustva_engine.missing_receipts(
            session, period_start=period_start, period_end=period_end
        )
        period.payload = payload.to_dict()
        period.missing_receipts = [g.to_dict() for g in gaps]
        period.preview_sent_at = now_utc()
        await session.flush()
        await record(
            session,
            actor=AuditActor.SCHEDULER,
            action="ustva.preview_sent",
            entity_type="ustva_period",
            entity_id=str(period.id),
            payload={"year": year, "quarter": quarter, "missing_count": len(gaps)},
        )
    msg_lines = [
        f"📊 *UStVA Q{quarter}/{year} preview*",
        "",
        f"Output VAT: {payload.output_vat} EUR",
        f"Input VAT: {payload.input_vat} EUR",
        f"Zahllast: {payload.balance} EUR",
    ]
    if gaps:
        msg_lines.append("")
        msg_lines.append(f"⚠️ {len(gaps)} missing receipts:")
        for gap in gaps[:10]:
            msg_lines.append(f"• {gap.name} (~{gap.expected_total} EUR)")
    msg_lines.append("")
    msg_lines.append("Use /approve_ustva once you've reviewed.")
    await notifier.send("\n".join(msg_lines))


async def dunning_job(today: date | None = None) -> None:
    """Daily scan for overdue invoices — drafts go to Telegram, not the wire."""
    enabled, reason = dunning_engine.is_enabled()
    if not enabled:
        log.info("scheduler.dunning.skipped", reason=reason)
        return
    today = today or today_local()
    notifier = TelegramNotifier()
    async with session_scope() as session:
        drafts = await dunning_engine.compute_drafts(session, today=today)
        new_runs: list[dunning_engine.Draft] = []
        from uuid import UUID

        for draft in drafts:
            stmt = (
                select(DunningRun)
                .where(DunningRun.invoice_id == UUID(draft.invoice_id))
                .where(DunningRun.mahnstufe == draft.mahnstufe)
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing is not None:
                continue
            run = DunningRun(
                invoice_id=UUID(draft.invoice_id),
                mahnstufe=draft.mahnstufe,
                draft_text=draft.text,
                interest_amount=float(draft.interest),
                fee_amount=float(draft.fee),
            )
            session.add(run)
            await session.flush()
            await record(
                session,
                actor=AuditActor.SCHEDULER,
                action="dunning.prepared",
                entity_type="dunning_run",
                entity_id=str(run.id),
                payload={
                    "invoice_id": draft.invoice_id,
                    "mahnstufe": draft.mahnstufe,
                },
            )
            new_runs.append(draft)
    for draft in new_runs:
        await notifier.send(
            f"📨 *Mahnung draft (stufe {draft.mahnstufe})*\n"
            f"Invoice {draft.invoice_number or draft.invoice_id} — "
            f"{draft.days_overdue} days overdue, gross {draft.gross} EUR.\n"
            f"Run `/send_mahnung {draft.invoice_id}` to approve and send."
        )


async def liquidity_weekly_job(today: date | None = None) -> None:
    """Weekly liquidity snapshot — Monday 08:00."""
    enabled, reason = liquidity_engine.is_enabled()
    if not enabled:
        log.info("scheduler.liquidity.skipped", reason=reason)
        return
    today = today or today_local()
    notifier = TelegramNotifier()
    async with session_scope() as session:
        comp = await liquidity_engine.compute_snapshot(session, as_of=today)
        snap = LiquiditySnapshot(
            opening_balance=float(comp.opening_balance),
            runway_date=comp.runway_date,
            scheduled_outflows=comp.scheduled_outflows,
            expected_inflows=comp.expected_inflows,
            alerts=comp.alerts,
        )
        session.add(snap)
        await session.flush()
        await record(
            session,
            actor=AuditActor.SCHEDULER,
            action="liquidity.snapshot.created",
            entity_type="liquidity_snapshot",
            entity_id=str(snap.id),
            payload={
                "runway_date": comp.runway_date.isoformat() if comp.runway_date else None,
                "alerts": len(comp.alerts),
            },
        )
    lines = [
        "💧 *Liquidity weekly digest*",
        "",
        f"Opening balance: {comp.opening_balance} EUR",
        f"Monthly burn: {comp.monthly_burn} EUR",
    ]
    if comp.runway_date is not None:
        lines.append(f"Runway through: {comp.runway_date.isoformat()}")
    else:
        lines.append("Runway: > 18 months (no negative balance projected)")
    if comp.unbilled_potential > Decimal("0"):
        lines.append(f"Potential (unbilled time): {comp.unbilled_potential} EUR")
    for alert in comp.alerts:
        lines.append(f"⚠️ {alert.get('kind')} — {alert}")
    await notifier.send("\n".join(lines))


async def datev_export_job(today: date | None = None) -> None:
    """Annual DATEV export — runs Jan 15th for the prior calendar year."""
    enabled, reason = datev_exporter.is_enabled()
    if not enabled:
        log.info("scheduler.datev.skipped", reason=reason)
        return
    today = today or today_local()
    year = today.year - 1
    notifier = TelegramNotifier()
    async with session_scope() as session:
        result = await datev_exporter.export_year(session, year)
    await notifier.send(
        f"📦 *DATEV export {year}* generated\n"
        f"CSV: `{result.csv_path}`\n"
        f"Invoices: {result.invoice_count} · Receipts: {result.receipt_count}\n"
        f"(Drive upload + advisor email: Phase 3.)"
    )
