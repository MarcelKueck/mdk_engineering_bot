"""Compute drafts for the Mahnwesen-Automat — pure functions over Invoices.

Stages (B2B):
- ``+14d`` past due  → ``Zahlungserinnerung``
- ``+30d`` past due  → ``1. Mahnung``
- ``+45d`` past due  → ``2. Mahnung`` with Verzugszinsen + Mahngebühr

Interest is Bundesbank Basiszinssatz + 9 pp on the invoice gross,
prorated by days overdue (act/365). See :data:`config.BASISZINSSATZ`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.config import get_settings
from mdk_bot.core.models import Invoice, InvoiceStatus


def is_enabled() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.FEATURE_DUNNING:
        return False, "FEATURE_DUNNING=false"
    return True, ""


# Stage thresholds (days past due_date).
STAGE_THRESHOLDS: list[tuple[int, int]] = [
    # (days_past_due, mahnstufe)
    (14, 1),
    (30, 2),
    (45, 3),
]


def next_mahnstufe(*, days_overdue: int, current: int) -> int | None:
    """Return the next stage to send for an invoice, or None if nothing to do."""
    candidate = None
    for threshold, stage in STAGE_THRESHOLDS:
        if days_overdue >= threshold and stage > current:
            candidate = stage
    return candidate


def interest_amount(
    *, gross: Decimal, days_overdue: int, basiszinssatz: Decimal, margin: Decimal
) -> Decimal:
    """Compute Verzugszinsen using (Basiszinssatz + margin) × gross × days/365."""
    if days_overdue <= 0:
        return Decimal("0")
    rate_pct = basiszinssatz + margin
    interest = gross * (rate_pct / Decimal("100")) * (Decimal(days_overdue) / Decimal("365"))
    return interest.quantize(Decimal("0.01"))


@dataclass(frozen=True)
class Draft:
    """A single prepared Mahnung — ready for operator approval."""

    invoice_id: str
    invoice_number: str | None
    mahnstufe: int
    days_overdue: int
    gross: Decimal
    interest: Decimal
    fee: Decimal
    text: str


_STAGE_LABEL = {
    1: "Zahlungserinnerung",
    2: "1. Mahnung",
    3: "2. Mahnung mit Verzugszinsen",
}


def _draft_text(
    *,
    stage: int,
    invoice: Invoice,
    days_overdue: int,
    interest: Decimal,
    fee: Decimal,
) -> str:
    label = _STAGE_LABEL[stage]
    invoice_number = invoice.number or "(ohne Nummer)"
    due = invoice.due_date.isoformat() if invoice.due_date else "?"
    gross = Decimal(str(invoice.total_gross or 0)).quantize(Decimal("0.01"))
    if stage == 1:
        body = (
            f"Sehr geehrte Damen und Herren,\n\n"
            f"unsere Rechnung {invoice_number} vom {due} über "
            f"{gross} EUR ist seit {days_overdue} Tagen offen. "
            f"Möglicherweise hat sich die Zahlung mit dieser Erinnerung "
            f"überschnitten — in diesem Fall bitte ich um Entschuldigung. "
            f"Andernfalls bitte ich um zeitnahen Ausgleich.\n\n"
            f"Mit freundlichen Grüßen\nMarcel Kück"
        )
    elif stage == 2:
        body = (
            f"Sehr geehrte Damen und Herren,\n\n"
            f"trotz unserer Zahlungserinnerung ist unsere Rechnung "
            f"{invoice_number} vom {due} über {gross} EUR weiterhin "
            f"offen ({days_overdue} Tage überfällig). Ich bitte um "
            f"Ausgleich innerhalb von 7 Tagen.\n\n"
            f"Mit freundlichen Grüßen\nMarcel Kück"
        )
    else:
        body = (
            f"Sehr geehrte Damen und Herren,\n\n"
            f"unsere Rechnung {invoice_number} vom {due} über {gross} EUR "
            f"ist seit {days_overdue} Tagen überfällig. Ich mache hiermit "
            f"die gesetzlichen Verzugszinsen geltend:\n"
            f"  Verzugszinsen: {interest} EUR\n"
            f"  Mahngebühr:    {fee} EUR\n"
            f"  Gesamtforderung: {(gross + interest + fee).quantize(Decimal('0.01'))} EUR\n\n"
            f"Ich bitte um Ausgleich innerhalb von 7 Tagen — andernfalls "
            f"behalte ich mir weitere rechtliche Schritte vor.\n\n"
            f"Mit freundlichen Grüßen\nMarcel Kück"
        )
    return f"[{label}]\n\n{body}"


def _draft_for_invoice(invoice: Invoice, *, today: date) -> Draft | None:
    if invoice.due_date is None or invoice.total_gross is None:
        return None
    days_overdue = (today - invoice.due_date).days
    stage = next_mahnstufe(days_overdue=days_overdue, current=invoice.mahnstufe)
    if stage is None:
        return None
    settings = get_settings()
    gross = Decimal(str(invoice.total_gross))
    interest = (
        interest_amount(
            gross=gross,
            days_overdue=days_overdue,
            basiszinssatz=Decimal(str(settings.BASISZINSSATZ)),
            margin=Decimal(str(settings.DUNNING_B2B_MARGIN)),
        )
        if stage == 3
        else Decimal("0")
    )
    fee = Decimal(str(settings.DUNNING_FEE_AMOUNT)) if stage == 3 else Decimal("0")
    return Draft(
        invoice_id=str(invoice.id),
        invoice_number=invoice.number,
        mahnstufe=stage,
        days_overdue=days_overdue,
        gross=gross,
        interest=interest,
        fee=fee,
        text=_draft_text(
            stage=stage,
            invoice=invoice,
            days_overdue=days_overdue,
            interest=interest,
            fee=fee,
        ),
    )


async def compute_drafts(session: AsyncSession, *, today: date) -> list[Draft]:
    """Scan open/overdue invoices and produce one Draft per actionable item."""
    rows = (
        (
            await session.execute(
                select(Invoice).where(
                    Invoice.status.in_([InvoiceStatus.OPEN, InvoiceStatus.OVERDUE])
                )
            )
        )
        .scalars()
        .all()
    )
    drafts: list[Draft] = []
    cutoff = today - timedelta(days=14)
    for invoice in rows:
        if invoice.due_date is None or invoice.due_date > cutoff:
            continue
        draft = _draft_for_invoice(invoice, today=today)
        if draft is not None:
            drafts.append(draft)
    return drafts
