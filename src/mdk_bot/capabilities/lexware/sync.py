"""Reconcile data pulled from Lexware Office into our local entities.

The sync is idempotent and keyed on ``lexware_id``: existing rows are
updated in place; new rows are inserted. Every upsert/insert writes an
``audit_log`` entry with actor ``scheduler``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.lexware.client import LexwareClient, LexwareError
from mdk_bot.config import get_settings
from mdk_bot.core.audit import record
from mdk_bot.core.models import (
    AuditActor,
    Invoice,
    InvoiceStatus,
    Organization,
    Receipt,
    ReceiptStatus,
    Transaction,
    TransactionDirection,
)
from mdk_bot.shared.logging import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class SyncStats:
    """Counters reported by :func:`run_sync` for logs / Telegram digest."""

    contacts_created: int = 0
    contacts_updated: int = 0
    invoices_created: int = 0
    invoices_updated: int = 0
    receipts_created: int = 0
    receipts_updated: int = 0
    transactions_created: int = 0
    transactions_updated: int = 0

    def to_dict(self) -> dict[str, int]:
        return self.__dict__.copy()


def is_enabled() -> tuple[bool, str]:
    """Return ``(enabled, reason_when_disabled)`` for log clarity."""
    settings = get_settings()
    if not settings.FEATURE_LEXWARE_SYNC:
        return False, "FEATURE_LEXWARE_SYNC=false"
    if not settings.LEXWARE_API_KEY:
        return False, "LEXWARE_API_KEY missing"
    return True, ""


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (TypeError, ValueError):
        return None


def _invoice_status(raw: str | None) -> InvoiceStatus:
    if not raw:
        return InvoiceStatus.DRAFT
    raw = raw.lower()
    if raw == "paid":
        return InvoiceStatus.PAID
    if raw == "overdue":
        return InvoiceStatus.OVERDUE
    if raw == "cancelled":
        return InvoiceStatus.CANCELLED
    if raw == "draft":
        return InvoiceStatus.DRAFT
    return InvoiceStatus.OPEN


async def _upsert_organization(
    session: AsyncSession, contact: dict[str, Any]
) -> tuple[Organization, bool]:
    """Find by ``lexware_id`` or by name; update / create as needed."""
    lex_id = contact.get("id")
    name = (
        (contact.get("company") or {}).get("name")
        or (contact.get("person") or {}).get("lastName")
        or "unnamed"
    )
    existing = None
    if lex_id:
        stmt = select(Organization).where(Organization.lexware_id == lex_id)
        existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        org = Organization(name=name, lexware_id=lex_id)
        session.add(org)
        await session.flush()
        return org, True
    existing.name = name
    return existing, False


async def _sync_contacts(session: AsyncSession, client: LexwareClient) -> tuple[int, int]:
    created = updated = 0
    async for contact in client.list_contacts():
        _, was_new = await _upsert_organization(session, contact)
        if was_new:
            created += 1
        else:
            updated += 1
    return created, updated


async def _sync_invoices(session: AsyncSession, client: LexwareClient) -> tuple[int, int]:
    created = updated = 0
    org_by_lex: dict[str, Organization] = {}
    async for voucher in client.list_invoices():
        lex_id = voucher.get("id")
        if not lex_id:
            continue
        stmt = select(Invoice).where(Invoice.lexware_id == lex_id)
        invoice = (await session.execute(stmt)).scalar_one_or_none()
        was_new = invoice is None
        if invoice is None:
            invoice = Invoice(lexware_id=lex_id)
            session.add(invoice)

        invoice.number = voucher.get("voucherNumber")
        invoice.issue_date = _parse_date(voucher.get("voucherDate"))
        invoice.due_date = _parse_date(voucher.get("dueDate"))
        invoice.total_gross = float(_decimal_or_none(voucher.get("totalAmount")) or 0)
        invoice.total_net = float(_decimal_or_none(voucher.get("openAmount")) or 0)
        invoice.currency = voucher.get("currency") or "EUR"
        invoice.status = _invoice_status(voucher.get("voucherStatus"))
        if invoice.status == InvoiceStatus.PAID:
            invoice.paid_date = invoice.paid_date or _parse_date(voucher.get("paidDate"))
        contact_id = voucher.get("contactId")
        if contact_id and contact_id in org_by_lex:
            invoice.customer_org_id = org_by_lex[contact_id].id
        elif contact_id:
            stmt2 = select(Organization).where(Organization.lexware_id == contact_id)
            org = (await session.execute(stmt2)).scalar_one_or_none()
            if org is not None:
                org_by_lex[contact_id] = org
                invoice.customer_org_id = org.id
        invoice.metadata_json = {"raw": voucher}
        await session.flush()
        await record(
            session,
            actor=AuditActor.SCHEDULER,
            action="lexware.invoice.created" if was_new else "lexware.invoice.updated",
            entity_type="invoice",
            entity_id=str(invoice.id),
            payload={"lexware_id": lex_id, "number": invoice.number},
        )
        if was_new:
            created += 1
        else:
            updated += 1
    return created, updated


async def _sync_receipts(session: AsyncSession, client: LexwareClient) -> tuple[int, int]:
    created = updated = 0
    async for voucher in client.list_vouchers():
        lex_id = voucher.get("id")
        if not lex_id:
            continue
        stmt = select(Receipt).where(Receipt.lexware_id == lex_id)
        receipt = (await session.execute(stmt)).scalar_one_or_none()
        was_new = receipt is None
        if receipt is None:
            receipt = Receipt(lexware_id=lex_id)
            session.add(receipt)
        receipt.date = _parse_date(voucher.get("voucherDate"))
        receipt.total = float(_decimal_or_none(voucher.get("totalAmount")) or 0)
        receipt.status = (
            ReceiptStatus.MATCHED
            if voucher.get("voucherStatus") == "paid"
            else ReceiptStatus.PENDING
        )
        receipt.metadata_json = {"raw": voucher}
        await session.flush()
        await record(
            session,
            actor=AuditActor.SCHEDULER,
            action="lexware.receipt.created" if was_new else "lexware.receipt.updated",
            entity_type="receipt",
            entity_id=str(receipt.id),
            payload={"lexware_id": lex_id},
        )
        if was_new:
            created += 1
        else:
            updated += 1
    return created, updated


async def _sync_transactions(session: AsyncSession, client: LexwareClient) -> tuple[int, int]:
    created = updated = 0
    async for tx in client.list_transactions():
        lex_id = tx.get("id")
        if not lex_id:
            continue
        stmt = select(Transaction).where(Transaction.lexware_match_id == lex_id)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        was_new = existing is None
        if existing is None:
            existing = Transaction(lexware_match_id=lex_id)
            session.add(existing)
        amount = float(_decimal_or_none(tx.get("amount")) or 0)
        existing.amount = amount
        existing.currency = tx.get("currency") or "EUR"
        existing.counterparty = tx.get("counterparty")
        existing.reference = tx.get("reference")
        existing.account = tx.get("account") or "lexware"
        existing.direction = TransactionDirection.IN if amount >= 0 else TransactionDirection.OUT
        existing.metadata_json = {"raw": tx}
        await session.flush()
        if was_new:
            created += 1
        else:
            updated += 1
    return created, updated


async def run_sync(session: AsyncSession) -> SyncStats:
    """Pull contacts → invoices → receipts → transactions, in that order.

    Order matters: invoices reference the orgs created in the contacts pass.
    """
    enabled, reason = is_enabled()
    if not enabled:
        log.info("lexware.sync.skipped", reason=reason)
        return SyncStats()

    try:
        async with LexwareClient() as client:
            contacts_c, contacts_u = await _sync_contacts(session, client)
            invoices_c, invoices_u = await _sync_invoices(session, client)
            receipts_c, receipts_u = await _sync_receipts(session, client)
            transactions_c, transactions_u = await _sync_transactions(session, client)
    except LexwareError as exc:
        log.error("lexware.sync.failed", error=str(exc))
        return SyncStats()

    stats = SyncStats(
        contacts_created=contacts_c,
        contacts_updated=contacts_u,
        invoices_created=invoices_c,
        invoices_updated=invoices_u,
        receipts_created=receipts_c,
        receipts_updated=receipts_u,
        transactions_created=transactions_c,
        transactions_updated=transactions_u,
    )
    await record(
        session,
        actor=AuditActor.SCHEDULER,
        action="lexware.sync.completed",
        entity_type="lexware",
        entity_id=None,
        payload=stats.to_dict(),
    )
    log.info("lexware.sync.completed", **stats.to_dict())
    return stats
