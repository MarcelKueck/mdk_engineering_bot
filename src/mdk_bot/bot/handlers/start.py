"""``/start`` — welcome the operator and list main commands."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from mdk_bot.bot.handlers._common import operator_handler, reply_md

WELCOME = """\
👋 *MDK Engineering Bot*

I remind you about tax and admin obligations and help with tasks, anchors,
finance, time tracking, UStVA, Mahnwesen, liquidity, VIES, and DATEV.

*Reminders & tasks*
• `/today` · `/week` · `/upcoming N` — what's due
• `/list [category]` · `/details <id>` — catalog
• `/done <id>` · `/skip <id>` — set status
• `/anchor <field> <YYYY-MM-DD>` · `/anchors` — anchor dates
• `/pause [hours]` · `/resume` — pause/resume notifications
• `/adhoc` — ad-hoc rules

*Finance (Phase 2)*
• `/finance` — open/overdue invoices, last Lexware sync
• `/sync_now` — pull Lexware now
• `/expenses` · `/expense_add <name> <amount> [cadence]` · `/expense_edit` · `/expense_rm`
• `/log <hours> [project] [note]` · `/hours [week|month]` · `/unbilled`
• `/ustva` — current quarter preview · `/approve_ustva` — operator approval
• `/runway` (or `/liquidity`) — runway view from known facts
• `/send_mahnung <invoice-prefix>` — approve a Mahnung draft
• `/vat <VAT-ID>` — qualified VIES check
• `/datev_export <year>` — generate a DATEV pack

`/help` — show this help
"""


@operator_handler
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the welcome message."""
    await reply_md(update, WELCOME)
