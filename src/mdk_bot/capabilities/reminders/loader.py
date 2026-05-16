"""Read ``obligations.json`` and upsert into the database.

This is intentionally idempotent — running the loader twice is a no-op.
The same module loads ad-hoc rules into a single-row JSON table.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mdk_bot.core.models import AdhocRules, Obligation
from mdk_bot.shared.logging import get_logger

log = get_logger(__name__)


class ObligationSpec(BaseModel):
    """Schema for one entry of ``obligations.json``."""

    id: str
    title: str
    category: str
    recurrence: str
    lead_time_days: int = 0
    action: str
    tool: str
    mandatory: bool | str = False
    estimated_minutes: int = 0
    penalty: str | None = None
    skip_if: str | None = None
    anchor_date_field: str | None = None
    # Free-form extras tolerated (e.g. ``trigger``); kept in raw payload.
    model_config = {"extra": "allow"}


class CatalogFile(BaseModel):
    """Top-level schema for the JSON file."""

    obligations: list[ObligationSpec]
    ad_hoc_rules: list[dict[str, Any]] = Field(default_factory=list)


def _parse_catalog(path: Path) -> CatalogFile:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return CatalogFile.model_validate(raw)


def _normalize_mandatory(value: bool | str) -> tuple[bool, str | None]:
    """Catalog allows ``mandatory`` to be a bool or a conditional string."""
    if isinstance(value, bool):
        return value, None
    # Strings like ``"bei EU-B2B-Umsätzen"`` mean "conditionally mandatory".
    return True, value


async def load_obligations_from_file(
    session: AsyncSession, path: Path | str
) -> tuple[int, int]:
    """Upsert obligations + ad-hoc rules from ``path``.

    Returns ``(obligations_count, adhoc_rule_count)``.
    """
    file_path = Path(path)
    catalog = _parse_catalog(file_path)

    log.info(
        "reminders.catalog.load",
        path=str(file_path),
        obligations=len(catalog.obligations),
        adhoc=len(catalog.ad_hoc_rules),
    )

    existing_ids = {
        row[0]
        for row in (await session.execute(select(Obligation.id))).all()
    }
    seen_ids: set[str] = set()

    for spec in catalog.obligations:
        mandatory_bool, mandatory_label = _normalize_mandatory(spec.mandatory)
        raw_payload = spec.model_dump(mode="json", exclude_none=False)
        obligation = await session.get(Obligation, spec.id)
        if obligation is None:
            obligation = Obligation(id=spec.id)
            session.add(obligation)
        obligation.title = spec.title
        obligation.category = spec.category
        obligation.recurrence = spec.recurrence
        obligation.lead_time_days = spec.lead_time_days
        obligation.action = spec.action
        obligation.tool = spec.tool
        obligation.mandatory = mandatory_bool
        obligation.mandatory_label = mandatory_label
        obligation.estimated_minutes = spec.estimated_minutes
        obligation.penalty = spec.penalty
        obligation.skip_if = spec.skip_if
        obligation.anchor_date_field = spec.anchor_date_field
        obligation.raw = raw_payload
        seen_ids.add(spec.id)

    stale = existing_ids - seen_ids
    if stale:
        log.warning("reminders.catalog.stale_obligations", ids=sorted(stale))

    # ad-hoc singleton
    adhoc = await session.get(AdhocRules, 1)
    if adhoc is None:
        adhoc = AdhocRules(id=1, payload=catalog.ad_hoc_rules)
        session.add(adhoc)
    else:
        adhoc.payload = catalog.ad_hoc_rules

    await session.flush()
    return len(catalog.obligations), len(catalog.ad_hoc_rules)
