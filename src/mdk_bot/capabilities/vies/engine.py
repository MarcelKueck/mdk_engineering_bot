"""Persist a VIES result + generate a minimal PDF proof.

The PDF is intentionally simple: a one-page artifact with the query
inputs, the consultation number, and the timestamp. We piggyback on
``cryptography`` (already in deps) — no, that won't produce a PDF, so we
emit a hand-rolled minimal PDF. The format is well-documented and stable
enough for our "proof of when we asked, with the answer attached" use.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.vies.client import VIESClient, VIESError, VIESResult
from mdk_bot.config import get_settings
from mdk_bot.core.audit import record
from mdk_bot.core.models import AuditActor, VatValidation
from mdk_bot.core.time import now_utc
from mdk_bot.shared.logging import get_logger
from mdk_bot.shared.storage import LocalDiskStorage

log = get_logger(__name__)


def is_enabled() -> tuple[bool, str]:
    settings = get_settings()
    if not settings.FEATURE_VIES:
        return False, "FEATURE_VIES=false"
    if not settings.VIES_REQUESTER_VAT_ID:
        return False, "VIES_REQUESTER_VAT_ID missing"
    return True, ""


def _build_pdf(
    *,
    vat_id: str,
    requester: str,
    result: VIESResult,
    queried_at: datetime,
) -> bytes:
    """Emit a minimal one-page PDF with the proof details.

    Hand-rolled to avoid pulling in a heavy PDF dependency for a stub
    document. The output is a valid PDF 1.4 readable by any viewer.
    """
    text_lines = [
        "VIES VAT Validation",
        "",
        f"Queried at:           {queried_at.isoformat()}",
        f"VAT-ID checked:       {vat_id}",
        f"Requester VAT-ID:     {requester}",
        f"Consultation number:  {result.consultation_number or '-'}",
        f"Valid:                {'yes' if result.valid else 'NO'}",
        f"Name match:           {result.name_match or '-'}",
        f"Address match:        {result.address_match or '-'}",
    ]
    body_pieces: list[str] = ["BT", "/F1 12 Tf", "1 0 0 1 50 760 Tm"]
    for line in text_lines:
        body_pieces.append(f"({line}) Tj")
        body_pieces.append("0 -16 Td")
    body_pieces.append("ET")
    body_stream = "\n".join(body_pieces).encode("latin-1", errors="replace")
    stream_obj = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(body_stream), body_stream)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        stream_obj,
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode("latin-1"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_position = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF\n"
    )
    output.extend(trailer.encode("latin-1"))
    return bytes(output)


async def validate_vat(
    session: AsyncSession,
    vat_id: str,
    *,
    storage_root: Path | None = None,
) -> VatValidation:
    """Run a qualified VIES query and persist the result + PDF proof.

    Raises :class:`VIESError` if the module isn't configured or the
    upstream call fails — callers (bot handlers) catch and translate.
    """
    enabled, reason = is_enabled()
    if not enabled:
        raise VIESError(f"VIES disabled: {reason}")
    settings = get_settings()
    async with VIESClient() as client:
        result = await client.check(vat_id)
    queried_at = now_utc()
    pdf_bytes = _build_pdf(
        vat_id=vat_id.upper().replace(" ", ""),
        requester=settings.VIES_REQUESTER_VAT_ID,
        result=result,
        queried_at=queried_at,
    )
    storage = LocalDiskStorage(storage_root or Path("./data/vies"))
    key = f"{queried_at:%Y%m%d}-{vat_id.upper().replace(' ', '')}-{queried_at:%H%M%S}.pdf"
    pdf_key = await storage.put(key, pdf_bytes, content_type="application/pdf")

    validation = VatValidation(
        vat_id_queried=vat_id.upper().replace(" ", ""),
        requester_vat_id=settings.VIES_REQUESTER_VAT_ID,
        valid=result.valid,
        name_match=result.name_match,
        address_match=result.address_match,
        consultation_number=result.consultation_number,
        raw_response={"xml": result.raw[:8000]},
        pdf_storage_key=pdf_key,
        queried_at=queried_at,
    )
    session.add(validation)
    await session.flush()
    await record(
        session,
        actor=AuditActor.USER,
        action="vies.validated",
        entity_type="vat_validation",
        entity_id=str(validation.id),
        payload={
            "vat_id": validation.vat_id_queried,
            "valid": validation.valid,
            "consultation_number": validation.consultation_number,
        },
    )
    return validation
