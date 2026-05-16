"""Daily check: compute due dates, create instances, send notifications.

The engine is pure with respect to "the clock" — :func:`run_daily_check`
accepts ``today`` so it can be driven from tests. Notifications are
dispatched via the :class:`Notifier` protocol so tests can substitute a
recording fake.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.capabilities.reminders.formatter import (
    format_anchor_missing,
    format_notification,
)
from mdk_bot.capabilities.reminders.rrule import (
    next_anchor_occurrence,
    next_occurrences,
)
from mdk_bot.core.audit import record
from mdk_bot.core.models import (
    AnchorDate,
    AuditActor,
    NotificationLog,
    Obligation,
    ObligationInstance,
    ObligationInstanceStatus,
    PauseState,
)
from mdk_bot.core.time import now_utc, today_local
from mdk_bot.shared.logging import get_logger

log = get_logger(__name__)

ANCHOR_DRIVEN_IDS: set[str] = {
    "berufshaftpflicht_verlaengerung",
    "domain_verlaengerung",
    "est_vorauszahlung",
}
ANCHOR_FALLBACK_FIELDS: dict[str, str] = {
    "est_vorauszahlung": "est_vorauszahlung_aktiv",
}


class Notifier(Protocol):
    """Abstract sink for outbound user notifications."""

    async def send(self, text: str) -> int | None:
        """Send ``text`` to the operator and return the platform message id."""
        ...


@dataclass(frozen=True)
class DueComputation:
    """Result of computing a single obligation's next due-date(s)."""

    obligation_id: str
    due_date: date | None
    requires_anchor: bool
    anchor_field: str | None = None


async def _is_paused(session: AsyncSession, *, now: date) -> bool:
    row = await session.get(PauseState, 1)
    if row is None or row.paused_until is None:
        return False
    return row.paused_until.date() >= now


async def compute_due_dates(
    session: AsyncSession, *, today: date
) -> list[DueComputation]:
    """For every catalog obligation return its next due date (or ``None``)."""
    obligations = list(
        (await session.execute(select(Obligation))).scalars().all()
    )
    anchors = {
        row.field_name: row.date_value
        for row in (await session.execute(select(AnchorDate))).scalars().all()
    }

    results: list[DueComputation] = []
    for obligation in obligations:
        anchor_field = obligation.anchor_date_field
        is_anchor_driven = obligation.id in ANCHOR_DRIVEN_IDS

        if is_anchor_driven:
            effective_field = anchor_field or ANCHOR_FALLBACK_FIELDS.get(obligation.id)
            if effective_field is None or effective_field not in anchors:
                results.append(
                    DueComputation(
                        obligation_id=obligation.id,
                        due_date=None,
                        requires_anchor=True,
                        anchor_field=effective_field,
                    )
                )
                continue
            if anchor_field is not None:
                due = next_anchor_occurrence(anchors[anchor_field], after=today - timedelta(days=1))
                results.append(
                    DueComputation(
                        obligation_id=obligation.id,
                        due_date=due,
                        requires_anchor=False,
                        anchor_field=anchor_field,
                    )
                )
                continue

        try:
            occurrences = next_occurrences(
                obligation.recurrence, after=today - timedelta(days=1), count=1
            )
        except Exception as exc:
            log.error(
                "reminders.rrule.parse_failed",
                obligation_id=obligation.id,
                rrule=obligation.recurrence,
                error=str(exc),
            )
            continue
        if occurrences:
            results.append(
                DueComputation(
                    obligation_id=obligation.id,
                    due_date=occurrences[0],
                    requires_anchor=False,
                    anchor_field=anchor_field,
                )
            )
    return results


def _lead_time_label(*, today: date, due: date) -> str:
    """Bucket the notification by how close to due-date we are."""
    delta = (due - today).days
    if delta > 0:
        return f"lead-{delta}d"
    if delta == 0:
        return "due-today"
    return f"overdue-{abs(delta)}d"


async def _get_or_create_instance(
    session: AsyncSession, *, obligation_id: str, due_date: date
) -> ObligationInstance:
    stmt = (
        select(ObligationInstance)
        .where(ObligationInstance.obligation_id == obligation_id)
        .where(ObligationInstance.due_date == due_date)
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing
    instance = ObligationInstance(obligation_id=obligation_id, due_date=due_date)
    session.add(instance)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            raise
        return existing
    return instance


async def _record_notification(
    session: AsyncSession,
    *,
    instance_id,
    label: str,
) -> bool:
    """Insert a row in ``notification_log``; return False if already sent."""
    log_row = NotificationLog(obligation_instance_id=instance_id, lead_time_label=label)
    session.add(log_row)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return False
    return True


def _terminal(status: ObligationInstanceStatus) -> bool:
    return status in {ObligationInstanceStatus.DONE, ObligationInstanceStatus.SKIPPED}


async def run_daily_check(
    session: AsyncSession,
    notifier: Notifier,
    *,
    today: date | None = None,
) -> dict[str, int]:
    """Compute due-dates, create instances, dispatch notifications.

    Returns a small stats dict for logging / tests.
    """
    today = today or today_local()
    stats = {"notified": 0, "escalated": 0, "anchor_missing": 0, "skipped_paused": 0}

    if await _is_paused(session, now=today):
        log.info("reminders.engine.paused")
        stats["skipped_paused"] = 1
        return stats

    computations = await compute_due_dates(session, today=today)
    obligations_by_id = {
        row.id: row
        for row in (await session.execute(select(Obligation))).scalars().all()
    }

    for comp in computations:
        obligation = obligations_by_id[comp.obligation_id]
        if comp.requires_anchor:
            if today.weekday() == 0:  # Monday digest
                # Dedup against audit_log: one anchor-missing nudge per obligation per day.
                from mdk_bot.core.models import AuditLog

                start_of_today_utc = now_utc().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                exists_stmt = (
                    select(AuditLog)
                    .where(AuditLog.action == "reminders.anchor_missing")
                    .where(AuditLog.entity_id == obligation.id)
                    .where(AuditLog.created_at >= start_of_today_utc)
                )
                already = (await session.execute(exists_stmt)).scalar_one_or_none()
                if already is None:
                    await notifier.send(format_anchor_missing(obligation))
                    await record(
                        session,
                        actor=AuditActor.SCHEDULER,
                        action="reminders.anchor_missing",
                        entity_type="obligation",
                        entity_id=obligation.id,
                        payload={"anchor_field": comp.anchor_field},
                    )
                    stats["anchor_missing"] += 1
            continue

        assert comp.due_date is not None
        notify_window_start = comp.due_date - timedelta(days=obligation.lead_time_days)
        if today < notify_window_start:
            continue
        instance = await _get_or_create_instance(
            session, obligation_id=obligation.id, due_date=comp.due_date
        )
        if _terminal(instance.status):
            continue

        label = _lead_time_label(today=today, due=comp.due_date)
        if not await _record_notification(
            session, instance_id=instance.id, label=label
        ):
            continue

        text = format_notification(obligation, instance, today=today)
        message_id = await notifier.send(text)
        instance.notified_at = now_utc()
        instance.telegram_message_id = message_id
        if today > comp.due_date and obligation.mandatory:
            instance.status = ObligationInstanceStatus.ESCALATED
            stats["escalated"] += 1
        else:
            instance.status = ObligationInstanceStatus.NOTIFIED
        await session.flush()

        await record(
            session,
            actor=AuditActor.SCHEDULER,
            action="reminders.notify",
            entity_type="obligation_instance",
            entity_id=str(instance.id),
            payload={
                "obligation_id": obligation.id,
                "due_date": comp.due_date.isoformat(),
                "label": label,
            },
        )
        stats["notified"] += 1

    return stats
