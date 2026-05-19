"""Liquidity & runway view built from known, dated facts.

NOT a smooth balance projection — the operator has irregular income, so a
predicted income curve would be false precision. Headline: the date until
which the operator's current balance covers known outflows (recurring
expenses, Steuerrücklage, known tax dates) plus already-issued invoices
landing on their due dates.
"""

from mdk_bot.capabilities.liquidity.engine import (
    LiquidityComputation,
    compute_snapshot,
    is_enabled,
)

__all__ = ["LiquidityComputation", "compute_snapshot", "is_enabled"]
