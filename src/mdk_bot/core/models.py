"""ORM models for Phase 0+1 plus stub tables for later phases.

All business tables carry a ``tenant_id`` column with a constant default
so a future multi-tenant migration is column-only. Stub tables (those
documented at the bottom of the file) ship with minimal columns and a
docstring describing the fields future phases will add.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeEngine

from mdk_bot.config import get_settings
from mdk_bot.core.db import Base


def JSONType() -> TypeEngine[Any]:
    """JSONB on Postgres, generic JSON elsewhere — keeps tests SQLite-friendly."""
    return JSON().with_variant(JSONB(), "postgresql")


def StringArray() -> TypeEngine[Any]:
    """ARRAY(String) on Postgres, JSON list elsewhere."""
    return JSON().with_variant(PG_ARRAY(String()), "postgresql")


def UUIDType() -> TypeEngine[Any]:
    """Native UUID on Postgres, CHAR(36) elsewhere — driven by sa.Uuid."""
    return Uuid(as_uuid=True)


def _new_uuid() -> uuid.UUID:
    return uuid.uuid4()


def _default_tenant_id() -> uuid.UUID:
    return get_settings().DEFAULT_TENANT_ID


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ProjectStatus(str, enum.Enum):
    LEAD = "lead"
    QUOTE = "quote"
    ACTIVE = "active"
    PAUSED = "paused"
    DELIVERED = "delivered"
    INVOICED = "invoiced"
    PAID = "paid"
    CLOSED = "closed"
    LOST = "lost"


class TaskStatus(str, enum.Enum):
    TODO = "todo"
    DOING = "doing"
    DONE = "done"
    SKIPPED = "skipped"


class TaskSource(str, enum.Enum):
    MANUAL = "manual"
    OBLIGATION = "obligation"
    EMAIL = "email"
    AGENT = "agent"


class ObligationInstanceStatus(str, enum.Enum):
    PENDING = "pending"
    NOTIFIED = "notified"
    DONE = "done"
    SKIPPED = "skipped"
    ESCALATED = "escalated"


class AuditActor(str, enum.Enum):
    USER = "user"
    BOT = "bot"
    SCHEDULER = "scheduler"
    AGENT = "agent"


# ---------------------------------------------------------------------------
# Business tables
# ---------------------------------------------------------------------------


class Organization(Base):
    """A customer / vendor / partner company."""

    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    legal_form: Mapped[str | None] = mapped_column(String(64))
    vat_id: Mapped[str | None] = mapped_column(String(64))
    address: Mapped[dict[str, Any] | None] = mapped_column(JSONType())
    lexware_id: Mapped[str | None] = mapped_column(String(64), index=True)
    website: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(StringArray(), nullable=False, default=list)
    custom_fields: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    persons: Mapped[list[Person]] = relationship(back_populates="current_org")
    projects: Mapped[list[Project]] = relationship(back_populates="customer_org")


class Person(Base):
    """A contact person — typically attached to one org."""

    __tablename__ = "persons"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(64))
    current_org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    linkedin_url: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(StringArray(), nullable=False, default=list)
    custom_fields: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    current_org: Mapped[Organization | None] = relationship(back_populates="persons")


class Project(Base):
    """A piece of contracted work for an organization."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    customer_org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ProjectStatus.LEAD
    )
    hourly_rate: Mapped[float | None] = mapped_column(Numeric(10, 2))
    scope: Mapped[str | None] = mapped_column(Text)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(StringArray(), nullable=False, default=list)
    custom_fields: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    customer_org: Mapped[Organization | None] = relationship(back_populates="projects")


class Task(Base):
    """A unit of work — manual, generated from an obligation, or agent-proposed."""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[date | None] = mapped_column(Date, index=True)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TaskStatus.TODO
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("projects.id", ondelete="SET NULL")
    )
    person_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("persons.id", ondelete="SET NULL")
    )
    obligation_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("obligation_instances.id", ondelete="SET NULL")
    )
    source: Mapped[TaskSource] = mapped_column(
        Enum(TaskSource, name="task_source", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=TaskSource.MANUAL
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (CheckConstraint("priority BETWEEN 1 AND 5", name="ck_task_priority_range"),)


class Obligation(Base):
    """Canonical recurring obligation from ``obligations.json``."""

    __tablename__ = "obligations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recurrence: Mapped[str] = mapped_column(String(255), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    tool: Mapped[str] = mapped_column(String(255), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mandatory_label: Mapped[str | None] = mapped_column(String(255))
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    penalty: Mapped[str | None] = mapped_column(Text)
    skip_if: Mapped[str | None] = mapped_column(Text)
    anchor_date_field: Mapped[str | None] = mapped_column(String(128))
    raw: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False)


class ObligationInstance(Base):
    """A concrete due date generated from an :class:`Obligation`."""

    __tablename__ = "obligation_instances"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    obligation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("obligations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[ObligationInstanceStatus] = mapped_column(
        Enum(
            ObligationInstanceStatus,
            name="obligation_instance_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ObligationInstanceStatus.PENDING,
    )
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("obligation_id", "due_date", name="uq_obligation_instance_id_date"),
    )


class NotificationLog(Base):
    """Idempotency log for outbound notifications — prevents double-sends."""

    __tablename__ = "notification_log"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    obligation_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(),
        ForeignKey("obligation_instances.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_time_label: Mapped[str] = mapped_column(String(32), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "obligation_instance_id", "lead_time_label", name="uq_notify_instance_label"
        ),
    )


class AnchorDate(Base):
    """User-supplied date anchors (insurance expiry, domain expiry, etc.)."""

    __tablename__ = "anchor_dates"

    field_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    date_value: Mapped[date] = mapped_column(Date, nullable=False)
    set_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    set_by: Mapped[str] = mapped_column(String(64), nullable=False, default="user")


class PauseState(Base):
    """Single-row table — when populated, the bot is silent until ``paused_until``."""

    __tablename__ = "pause_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    paused_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (CheckConstraint("id = 1", name="ck_pause_state_singleton"),)


class AdhocRules(Base):
    """Single-row table holding the ad-hoc rule catalog (JSON payload)."""

    __tablename__ = "adhoc_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    payload: Mapped[list[dict[str, Any]]] = mapped_column(JSONType(), nullable=False, default=list)

    __table_args__ = (CheckConstraint("id = 1", name="ck_adhoc_rules_singleton"),)


class AuditLog(Base):
    """Append-only audit trail of mutations and bot/scheduler actions."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    actor: Mapped[AuditActor] = mapped_column(
        Enum(AuditActor, name="audit_actor", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


# ---------------------------------------------------------------------------
# Stub tables — created now so the schema is stable; future phases extend
# them via Alembic migrations rather than creating from scratch.
# ---------------------------------------------------------------------------


class Conversation(Base):
    """Future: conversation thread (Telegram, email, chat) — see Phase 2."""

    __tablename__ = "conversations"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, default="telegram")
    external_id: Mapped[str | None] = mapped_column(String(128))
    subject: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Message(Base):
    """Future: individual message in a :class:`Conversation`."""

    __tablename__ = "messages"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Document(Base):
    """Future: stored document (receipt, contract, scan) — see Phase 4."""

    __tablename__ = "documents"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Transaction(Base):
    """Future: bank / payment transaction."""

    __tablename__ = "transactions"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    booked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(8))
    counterparty: Mapped[str | None] = mapped_column(String(255))
    reference: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)


class Invoice(Base):
    """Future: invoice (mirror of Lexware record + augmentation)."""

    __tablename__ = "invoices"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    lexware_id: Mapped[str | None] = mapped_column(String(64), index=True)
    number: Mapped[str | None] = mapped_column(String(64))
    customer_org_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("organizations.id", ondelete="SET NULL")
    )
    issued_on: Mapped[date | None] = mapped_column(Date)
    due_on: Mapped[date | None] = mapped_column(Date)
    total: Mapped[float | None] = mapped_column(Numeric(12, 2))
    status: Mapped[str | None] = mapped_column(String(32))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)


class Receipt(Base):
    """Future: incoming receipt to attach to a transaction."""

    __tablename__ = "receipts"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    vendor: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    captured_on: Mapped[date | None] = mapped_column(Date)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType(), ForeignKey("documents.id", ondelete="SET NULL")
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)


class Event(Base):
    """Future: calendar event (Google Calendar mirror)."""

    __tablename__ = "events"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    external_id: Mapped[str | None] = mapped_column(String(255))
    title: Mapped[str | None] = mapped_column(String(255))
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)


class KnowledgeItem(Base):
    """Future: long-term knowledge / RAG corpus. Phase 3+ populates embeddings."""

    __tablename__ = "knowledge_items"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    title: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)


class ReadingItem(Base):
    """Future: read-it-later queue."""

    __tablename__ = "reading_items"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MedicalBill(Base):
    """Future: medical bill workflow (Beihilfe / private insurance reimbursement)."""

    __tablename__ = "medical_bills"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    provider: Mapped[str | None] = mapped_column(String(255))
    amount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    received_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str | None] = mapped_column(String(32))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)


class ProviderCredential(Base):
    """Future: encrypted credentials for external providers (Lexware, Gmail, …)."""

    __tablename__ = "provider_credentials"
    id: Mapped[uuid.UUID] = mapped_column(UUIDType(), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType(), nullable=False, default=_default_tenant_id
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_blob: Mapped[bytes | None] = mapped_column(LargeBinary)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONType(), nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_provider_credential_tenant_provider"),
    )


Index("ix_audit_log_entity", AuditLog.entity_type, AuditLog.entity_id)
