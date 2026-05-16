"""Notification formatting."""

from __future__ import annotations

from datetime import date

from mdk_bot.capabilities.reminders.formatter import (
    format_anchor_missing,
    format_notification,
)
from mdk_bot.core.models import ObligationInstance
from tests.factories import make_obligation


def test_format_notification_mandatory_has_warning() -> None:
    obligation = make_obligation(mandatory=True, penalty="10%")
    instance = ObligationInstance(obligation_id=obligation.id, due_date=date(2025, 4, 10))
    text = format_notification(obligation, instance)
    assert "🔔" in text
    assert "PFLICHT" in text
    assert "10%" in text
    assert "/done ustva_quartal" in text


def test_format_notification_optional_uses_recommendation() -> None:
    obligation = make_obligation(id="schaetzung_review", mandatory=False)
    instance = ObligationInstance(obligation_id=obligation.id, due_date=date(2025, 4, 15))
    text = format_notification(obligation, instance)
    assert "Empfohlen" in text
    assert "PFLICHT" not in text


def test_format_notification_zm_quartal_appendix() -> None:
    obligation = make_obligation(id="zm_quartal", skip_if="keine EU-B2B-Umsätze im Quartal")
    instance = ObligationInstance(obligation_id=obligation.id, due_date=date(2025, 4, 25))
    text = format_notification(obligation, instance)
    assert "/skip zm_quartal" in text


def test_format_anchor_missing_contains_field_name() -> None:
    obligation = make_obligation(
        id="berufshaftpflicht_verlaengerung",
        anchor_date_field="vertragsablauf_berufshaftpflicht",
    )
    text = format_anchor_missing(obligation)
    assert "vertragsablauf_berufshaftpflicht" in text
    assert "/anchor" in text
