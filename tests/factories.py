"""factory_boy factories used by the test suite."""

from __future__ import annotations

import factory

from mdk_bot.core.models import (
    Obligation,
    Organization,
    Person,
    Project,
    ProjectStatus,
    Task,
)


class OrganizationFactory(factory.Factory):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"Org {n}")


class PersonFactory(factory.Factory):
    class Meta:
        model = Person

    name = factory.Sequence(lambda n: f"Person {n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.name.lower().replace(' ', '.')}@example.com")


class ProjectFactory(factory.Factory):
    class Meta:
        model = Project

    name = factory.Sequence(lambda n: f"Project {n}")
    status = ProjectStatus.ACTIVE


class TaskFactory(factory.Factory):
    class Meta:
        model = Task

    title = factory.Sequence(lambda n: f"Task {n}")


def make_obligation(
    *,
    id: str = "ustva_quartal",
    title: str = "USt-Voranmeldung Quartal",
    category: str = "steuer",
    recurrence: str = "FREQ=QUARTERLY;BYMONTH=1,4,7,10;BYMONTHDAY=10",
    lead_time_days: int = 7,
    action: str = "Per ELSTER abgeben",
    tool: str = "ELSTER",
    mandatory: bool = True,
    estimated_minutes: int = 15,
    penalty: str | None = None,
    skip_if: str | None = None,
    anchor_date_field: str | None = None,
) -> Obligation:
    return Obligation(
        id=id,
        title=title,
        category=category,
        recurrence=recurrence,
        lead_time_days=lead_time_days,
        action=action,
        tool=tool,
        mandatory=mandatory,
        estimated_minutes=estimated_minutes,
        penalty=penalty,
        skip_if=skip_if,
        anchor_date_field=anchor_date_field,
        raw={"id": id},
    )
