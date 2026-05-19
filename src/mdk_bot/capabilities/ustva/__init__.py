"""UStVA Vorbereitung — quarterly VAT return preview + Belegvollständigkeit.

Phase 2 prepares the data and routes it past the operator for approval.
We deliberately do NOT submit to ELSTER — submission stays manual in
Lexware until a dedicated capability lands later.
"""

from mdk_bot.capabilities.ustva.engine import (
    Belegcheck,
    UstvaPayload,
    compute_payload,
    current_quarter,
    is_enabled,
    missing_receipts,
)

__all__ = [
    "Belegcheck",
    "UstvaPayload",
    "compute_payload",
    "current_quarter",
    "is_enabled",
    "missing_receipts",
]
