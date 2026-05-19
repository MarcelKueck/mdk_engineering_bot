"""Pydantic v2 schemas — request/response models for the API.

Kept in one module so they can be imported uniformly from routers and the
bot's API client. Each entity has a ``Create`` (input), ``Update`` (partial
input) and ``Read`` (output) variant.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

from mdk_bot.core.models import (
    AuditActor,
    ExpenseCadence,
    InvoiceStatus,
    ObligationInstanceStatus,
    ProjectStatus,
    ReceiptStatus,
    TaskSource,
    TaskStatus,
    UstvaStatus,
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


# -- Invoices -------------------------------------------------------------


class InvoiceBase(BaseModel):
    lexware_id: str | None = None
    number: str | None = None
    customer_org_id: UUID | None = None
    project_id: UUID | None = None
    issue_date: date | None = None
    due_date: date | None = None
    total_gross: float | None = None
    total_net: float | None = None
    currency: str = "EUR"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    paid_date: date | None = None
    mahnstufe: int = 0


class InvoiceRead(ORMModel, InvoiceBase):
    id: UUID
    tenant_id: UUID
    last_mahnung_at: datetime | None
    created_at: datetime
    updated_at: datetime


# -- Receipts -------------------------------------------------------------


class ReceiptRead(ORMModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    tenant_id: UUID
    lexware_id: str | None = None
    vendor_org_id: UUID | None = None
    project_id: UUID | None = None
    receipt_date: date | None = Field(
        default=None,
        validation_alias=AliasChoices("date", "receipt_date"),
        serialization_alias="date",
    )
    total: float | None = None
    vat: float | None = None
    category: str | None = None
    document_id: UUID | None = None
    status: ReceiptStatus = ReceiptStatus.PENDING
    created_at: datetime
    updated_at: datetime


# -- Recurring Expenses ---------------------------------------------------


class RecurringExpenseBase(BaseModel):
    name: str
    amount: float
    currency: str = "EUR"
    cadence: ExpenseCadence = ExpenseCadence.MONTHLY
    vendor_org_id: UUID | None = None
    category: str | None = None
    vat_rate: float | None = None
    active: bool = True
    effective_from: date | None = None
    effective_until: date | None = None
    next_amount: float | None = None
    next_amount_effective_from: date | None = None


class RecurringExpenseCreate(RecurringExpenseBase):
    pass


class RecurringExpenseUpdate(BaseModel):
    name: str | None = None
    amount: float | None = None
    currency: str | None = None
    cadence: ExpenseCadence | None = None
    vendor_org_id: UUID | None = None
    category: str | None = None
    vat_rate: float | None = None
    active: bool | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    next_amount: float | None = None
    next_amount_effective_from: date | None = None


class RecurringExpenseRead(ORMModel, RecurringExpenseBase):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime


# -- Time Entries ---------------------------------------------------------


class TimeEntryCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_date: date = Field(
        validation_alias=AliasChoices("date", "entry_date"),
        serialization_alias="date",
    )
    hours: float = Field(gt=0)
    project_id: UUID | None = None
    note: str | None = None
    billable: bool = True
    billed: bool = False
    invoice_id: UUID | None = None


class TimeEntryUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_date: date | None = Field(
        default=None,
        validation_alias=AliasChoices("date", "entry_date"),
        serialization_alias="date",
    )
    hours: float | None = Field(default=None, gt=0)
    project_id: UUID | None = None
    note: str | None = None
    billable: bool | None = None
    billed: bool | None = None
    invoice_id: UUID | None = None


class TimeEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    tenant_id: UUID
    entry_date: date = Field(
        validation_alias=AliasChoices("date", "entry_date"),
        serialization_alias="date",
    )
    hours: float
    project_id: UUID | None = None
    note: str | None = None
    billable: bool = True
    billed: bool = False
    invoice_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


# -- VAT Validation -------------------------------------------------------


class VatValidationRead(ORMModel):
    id: UUID
    tenant_id: UUID
    vat_id_queried: str
    requester_vat_id: str | None
    valid: bool
    name_match: str | None
    address_match: str | None
    consultation_number: str | None
    raw_response: dict[str, Any]
    invoice_id: UUID | None
    pdf_storage_key: str | None
    queried_at: datetime


# -- UStVA Period ---------------------------------------------------------


class UstvaPeriodRead(ORMModel):
    id: UUID
    tenant_id: UUID
    year: int
    quarter: int
    period_start: date
    period_end: date
    status: UstvaStatus
    payload: dict[str, Any]
    missing_receipts: list[dict[str, Any]]
    preview_sent_at: datetime | None
    approved_at: datetime | None
    submitted_at: datetime | None
    created_at: datetime


# -- Dunning --------------------------------------------------------------


class DunningRunRead(ORMModel):
    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    mahnstufe: int
    draft_text: str
    interest_amount: float
    fee_amount: float
    sent_at: datetime | None
    conversation_id: UUID | None
    created_at: datetime


# -- Liquidity ------------------------------------------------------------


class LiquiditySnapshotRead(ORMModel):
    id: UUID
    tenant_id: UUID
    created_at: datetime
    opening_balance: float
    runway_date: date | None
    scheduled_outflows: list[dict[str, Any]]
    expected_inflows: list[dict[str, Any]]
    alerts: list[dict[str, Any]]
