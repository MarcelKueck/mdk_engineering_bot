"""Tests for the DATEV exporter."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.datev.exporter import export_year
from mdk_bot.core.models import Invoice, InvoiceStatus, Receipt


async def test_export_year_writes_csv_and_metadata(session: AsyncSession, tmp_path: Path) -> None:
    session.add(
        Invoice(
            number="2025-001",
            issue_date=date(2025, 6, 1),
            total_gross=119.0,
            status=InvoiceStatus.PAID,
        )
    )
    session.add(Receipt(date=date(2025, 7, 15), total=50.0, vat=8.0))
    await session.commit()
    result = await export_year(session, 2025, output_dir=tmp_path)
    assert result.csv_path.exists()
    assert result.metadata_path.exists()
    assert result.invoice_count == 1
    assert result.receipt_count == 1

    rows = list(csv.reader(result.csv_path.read_text(encoding="utf-8").splitlines(), delimiter=";"))
    # Header + columns + 2 data rows
    assert len(rows) == 4
    assert rows[0][0] == "EXTF"


async def test_export_year_skips_other_years(session: AsyncSession, tmp_path: Path) -> None:
    session.add(
        Invoice(
            number="2024-001",
            issue_date=date(2024, 6, 1),
            total_gross=100.0,
            status=InvoiceStatus.PAID,
        )
    )
    await session.commit()
    result = await export_year(session, 2025, output_dir=tmp_path)
    assert result.invoice_count == 0
