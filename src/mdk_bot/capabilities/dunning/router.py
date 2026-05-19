"""Dunning API: list drafts, send (stubbed transport) a specific draft."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.api.deps import AuthDep, SessionDep
from mdk_bot.capabilities.dunning.engine import compute_drafts
from mdk_bot.core.audit import record
from mdk_bot.core.models import (
    AuditActor,
    Conversation,
    DunningRun,
    Invoice,
    Message,
)
from mdk_bot.core.schemas import DunningRunRead
from mdk_bot.core.time import now_utc, today_local

router = APIRouter(prefix="/dunning", tags=["dunning"], dependencies=[AuthDep])


@router.get("/runs", response_model=list[DunningRunRead])
async def list_runs(session: AsyncSession = SessionDep) -> list[DunningRun]:
    rows = (
        (await session.execute(select(DunningRun).order_by(DunningRun.created_at.desc())))
        .scalars()
        .all()
    )
    return list(rows)


@router.post("/prepare")
async def prepare(session: AsyncSession = SessionDep) -> dict[str, object]:
    """Compute drafts for the current date and persist DunningRun rows.

    Idempotent per ``(invoice_id, mahnstufe)``: re-running on the same day
    does not duplicate entries.
    """
    drafts = await compute_drafts(session, today=today_local())
    created: list[str] = []
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
                "interest": str(draft.interest),
                "fee": str(draft.fee),
            },
        )
        created.append(str(run.id))
    return {"drafted": len(created), "ids": created}


@router.post("/{run_id}/send", response_model=DunningRunRead)
async def send(run_id: UUID, session: AsyncSession = SessionDep) -> DunningRun:
    """Operator approval — "send" the Mahnung.

    Phase 2: email transport is stubbed. We persist a Conversation +
    Message representing the would-be email, mark the run sent, and bump
    the invoice's mahnstufe. Phase 3 swaps in real Gmail send.
    """
    run = await session.get(DunningRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="dunning run not found")
    if run.sent_at is not None:
        return run
    invoice = await session.get(Invoice, run.invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="invoice not found")
    # TODO(phase-3): Replace this stub with a real Gmail send.
    convo = Conversation(
        channel="email-stub",
        subject=f"Mahnung Rechnung {invoice.number or invoice.id}",
        metadata_json={"invoice_id": str(invoice.id), "stub": True},
    )
    session.add(convo)
    await session.flush()
    session.add(
        Message(
            conversation_id=convo.id,
            role="outbound",
            content=run.draft_text,
            metadata_json={"mahnstufe": run.mahnstufe},
        )
    )
    run.sent_at = now_utc()
    run.conversation_id = convo.id
    invoice.mahnstufe = max(invoice.mahnstufe, run.mahnstufe)
    invoice.last_mahnung_at = now_utc()
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="dunning.sent",
        entity_type="dunning_run",
        entity_id=str(run.id),
        payload={
            "invoice_id": str(invoice.id),
            "mahnstufe": run.mahnstufe,
            "stub": True,
        },
    )
    return run
