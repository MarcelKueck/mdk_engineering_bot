"""Lexware Office (lexoffice) sync capability.

Daily pull of contacts, invoices, vouchers, transactions from the
lexoffice REST API. Idempotent; keyed on ``lexware_id``. Gated by
:data:`config.FEATURE_LEXWARE_SYNC` AND a non-empty ``LEXWARE_API_KEY``.
"""

from mdk_bot.capabilities.lexware.client import LexwareClient
from mdk_bot.capabilities.lexware.sync import is_enabled, run_sync

__all__ = ["LexwareClient", "is_enabled", "run_sync"]
