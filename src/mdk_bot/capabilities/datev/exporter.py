"""Generate a DATEV-compatible Buchungsstapel CSV from local finance data.

The EXTF (DATEV "Buchungsstapel") format starts with a metadata header
row and a column-name row, then one row per posting. For Phase 2 we
emit only the figures we have from the Lexware sync — Sollkonto and
Gegenkonto default to placeholders and need post-processing by the tax
advisor. See:
https://developer.datev.de/datev/platform/de/dtvf
"""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.config import get_settings
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, Invoice, Receipt


def is_enabled() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.FEATURE_DATEV:
        return False, "FEATURE_DATEV=false"
    return True, ""


@dataclass(frozen=True)
class DatevExport:
    """Result of one export run — file paths + a small row counter."""

    csv_path: Path
    metadata_path: Path
    invoice_count: int
    receipt_count: int


_HEADER_TMPL: list[Any] = [
    "EXTF",
    700,  # version
    21,  # data category: Buchungsstapel
    "Buchungsstapel",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "EUR",
]

_COLUMNS = [
    "Umsatz (ohne Soll/Haben-Kz)",
    "Soll/Haben-Kennzeichen",
    "WKZ Umsatz",
    "Kurs",
    "Basis-Umsatz",
    "WKZ Basis-Umsatz",
    "Konto",
    "Gegenkonto (ohne BU-Schlüssel)",
    "BU-Schlüssel",
    "Belegdatum",
    "Belegfeld 1",
    "Belegfeld 2",
    "Skonto",
    "Buchungstext",
]


def _format_row(
    *,
    amount: float,
    soll_haben: str,
    konto: str,
    gegenkonto: str,
    belegdatum: date,
    beleg_nr: str,
    text: str,
) -> list[Any]:
    return [
        f"{abs(amount):.2f}".replace(".", ","),
        soll_haben,
        "EUR",
        "",
        "",
        "",
        konto,
        gegenkonto,
        "",
        belegdatum.strftime("%d%m"),
        beleg_nr,
        "",
        "",
        text,
    ]


async def export_year(
    session: AsyncSession,
    year: int,
    *,
    output_dir: Path | None = None,
) -> DatevExport:
    """Build the CSV + JSON metadata files for ``year`` and write to disk."""
    settings = get_settings()
    output_dir = output_dir or Path(settings.DATEV_EXPORT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    invoices = (
        (
            await session.execute(
                select(Invoice)
                .where(Invoice.issue_date.is_not(None))
                .where(Invoice.issue_date >= date(year, 1, 1))
                .where(Invoice.issue_date <= date(year, 12, 31))
            )
        )
        .scalars()
        .all()
    )
    receipts = (
        (
            await session.execute(
                select(Receipt)
                .where(Receipt.date.is_not(None))
                .where(Receipt.date >= date(year, 1, 1))
                .where(Receipt.date <= date(year, 12, 31))
            )
        )
        .scalars()
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_ALL)
    writer.writerow(_HEADER_TMPL)
    writer.writerow(_COLUMNS)

    for invoice in invoices:
        if invoice.total_gross is None or invoice.issue_date is None:
            continue
        writer.writerow(
            _format_row(
                amount=float(invoice.total_gross),
                soll_haben="S",
                konto="1400",  # Forderungen aL+L (SKR03 default — adjust per advisor)
                gegenkonto="8400",  # Erlöse 19% USt (default placeholder)
                belegdatum=invoice.issue_date,
                beleg_nr=invoice.number or "",
                text=f"Invoice {invoice.number or invoice.id}",
            )
        )

    for receipt in receipts:
        if receipt.total is None or receipt.date is None:
            continue
        writer.writerow(
            _format_row(
                amount=float(receipt.total),
                soll_haben="H",
                konto="3300",  # Wareneingang (default placeholder)
                gegenkonto="1200",  # Bank (default placeholder)
                belegdatum=receipt.date,
                beleg_nr=str(receipt.lexware_id or ""),
                text=receipt.category or "Expense",
            )
        )

    csv_path = output_dir / f"datev-{year}.csv"
    csv_path.write_text(buf.getvalue(), encoding="utf-8")

    metadata = {
        "year": year,
        "generated_at": "auto",
        "invoice_count": len(invoices),
        "receipt_count": len(receipts),
        "format": "EXTF Buchungsstapel v700",
        "kontenrahmen": "SKR03 (placeholder accounts; review with advisor)",
        # TODO(phase-3): upload to Drive folder + email to tax advisor.
    }
    metadata_path = output_dir / f"datev-{year}.meta.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    await record(
        session,
        actor=AuditActor.USER,
        action="datev.exported",
        entity_type="datev_export",
        entity_id=str(year),
        payload={
            "csv_path": str(csv_path),
            "invoice_count": len(invoices),
            "receipt_count": len(receipts),
        },
    )
    return DatevExport(
        csv_path=csv_path,
        metadata_path=metadata_path,
        invoice_count=len(invoices),
        receipt_count=len(receipts),
    )
