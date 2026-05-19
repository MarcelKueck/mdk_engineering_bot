"""Recurring expenses capability — operator-managed catalog of subscriptions.

Always on (no feature flag). Exposes CRUD + a :func:`monthly_burn` helper
used by the liquidity module.
"""

from mdk_bot.capabilities.expenses.engine import (
    effective_amount,
    is_active_on,
    monthly_burn,
    normalize_to_monthly,
)

__all__ = ["effective_amount", "is_active_on", "monthly_burn", "normalize_to_monthly"]
