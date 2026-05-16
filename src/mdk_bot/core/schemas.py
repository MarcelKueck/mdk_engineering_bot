"""Pydantic v2 schemas — request/response models for the API.

Kept in one module so they can be imported uniformly from routers and the
bot's API client. Each entity has a ``Create`` (input), ``Update`` (partial
input) and ``Read`` (output) variant.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from mdk_bot.core.models import (
    AuditActor,
    ObligationInstanceStatus,
    ProjectStatus,
    TaskSource,
    TaskStatus,
)


class ORMModel(BaseModel):
    """Base config for read-side models — read from ORM attributes."""

    model_config = ConfigDict(from_attributes=True)


# -- Organizations --------------------------------------------------------


class OrganizationBase(BaseModel):
    name: str
    legal_form: str | None = None
    vat_id: str | None = None
    address: dict[str, Any] | None = None
    lexware_id: str | None = None
    website: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: str | None = None
    legal_form: str | None = None
    vat_id: str | None = None
    address: dict[str, Any] | None = None
    lexware_id: str | None = None
    website: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


class OrganizationRead(ORMModel, OrganizationBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


# -- Persons --------------------------------------------------------------


class PersonBase(BaseModel):
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    current_org_id: UUID | None = None
    linkedin_url: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    current_org_id: UUID | None = None
    linkedin_url: str | None = None
    notes: str | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


class PersonRead(ORMModel, PersonBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


# -- Projects -------------------------------------------------------------


class ProjectBase(BaseModel):
    name: str
    customer_org_id: UUID | None = None
    status: ProjectStatus = ProjectStatus.LEAD
    hourly_rate: float | None = None
    scope: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = None
    customer_org_id: UUID | None = None
    status: ProjectStatus | None = None
    hourly_rate: float | None = None
    scope: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    description: str | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


class ProjectRead(ORMModel, ProjectBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


# -- Tasks ----------------------------------------------------------------


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    due_date: date | None = None
    status: TaskStatus = TaskStatus.TODO
    priority: int = Field(default=3, ge=1, le=5)
    project_id: UUID | None = None
    person_id: UUID | None = None
    obligation_instance_id: UUID | None = None
    source: TaskSource = TaskSource.MANUAL


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    due_date: date | None = None
    status: TaskStatus | None = None
    priority: int | None = Field(default=None, ge=1, le=5)
    project_id: UUID | None = None
    person_id: UUID | None = None


class TaskRead(ORMModel, TaskBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    completed_at: datetime | None


# -- Obligations ----------------------------------------------------------


class ObligationRead(ORMModel):
    id: str
    title: str
    category: str
    recurrence: str
    lead_time_days: int
    action: str
    tool: str
    mandatory: bool
    mandatory_label: str | None
    estimated_minutes: int
    penalty: str | None
    skip_if: str | None
    anchor_date_field: str | None
    raw: dict[str, Any]


class ObligationInstanceRead(ORMModel):
    id: UUID
    obligation_id: str
    due_date: date
    status: ObligationInstanceStatus
    notified_at: datetime | None
    acknowledged_at: datetime | None
    telegram_message_id: int | None
    created_at: datetime


class ObligationInstanceWithObligation(ObligationInstanceRead):
    obligation: ObligationRead


# -- Anchors --------------------------------------------------------------


class AnchorDateRead(ORMModel):
    field_name: str
    date_value: date
    set_at: datetime
    set_by: str


class AnchorDateUpdate(BaseModel):
    date_value: date
    set_by: str = "user"


# -- Audit ----------------------------------------------------------------


class AuditLogRead(ORMModel):
    id: UUID
    actor: AuditActor
    action: str
    entity_type: str | None
    entity_id: str | None
    payload: dict[str, Any]
    created_at: datetime


# -- Health ---------------------------------------------------------------


class HealthStatus(BaseModel):
    status: str
    db: str
    redis: str


# -- Auth -----------------------------------------------------------------


class LoginRequest(BaseModel):
    token: str
