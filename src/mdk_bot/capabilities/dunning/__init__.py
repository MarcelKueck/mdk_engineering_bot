"""Mahnwesen-Automat — drafts payment reminders / Mahnungen for approval.

Daily scan of open invoices past their ``due_date``. Drafts go to
Telegram; nothing is sent until the operator runs ``/send_mahnung <id>``.
Email transport is stubbed until Phase 3 (Gmail integration).
"""

from mdk_bot.capabilities.dunning.engine import (
    Draft,
    compute_drafts,
    interest_amount,
    is_enabled,
    next_mahnstufe,
)

__all__ = [
    "Draft",
    "compute_drafts",
    "interest_amount",
    "is_enabled",
    "next_mahnstufe",
]
