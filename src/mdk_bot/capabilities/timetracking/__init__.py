"""Time tracking capability — operator logs hours, summaries, billing flags.

Always on. Replaces an external timer like Toggl with the minimum
viable surface: log, view, mark billed.
"""

from mdk_bot.capabilities.timetracking.engine import (
    hours_summary,
    unbilled_value,
)

__all__ = ["hours_summary", "unbilled_value"]
