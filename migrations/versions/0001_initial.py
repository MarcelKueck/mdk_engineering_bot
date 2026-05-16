"""initial schema — phase 0+1 tables and stub tables

Revision ID: 0001
Revises:
Create Date: 2025-01-01 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    project_status = sa.Enum(
        "lead",
        "quote",
        "active",
        "paused",
        "delivered",
        "invoiced",
        "paid",
        "closed",
        "lost",
        name="project_status",
    )
    task_status = sa.Enum("todo", "doing", "done", "skipped", name="task_status")
    task_source = sa.Enum("manual", "obligation", "email", "agent", name="task_source")
    instance_status = sa.Enum(
        "pending",
        "notified",
        "done",
        "skipped",
        "escalated",
        name="obligation_instance_status",
    )
    audit_actor = sa.Enum("user", "bot", "scheduler", "agent", name="audit_actor")

    # ----- organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("legal_form", sa.String(64)),
        sa.Column("vat_id", sa.String(64)),
        sa.Column("address", postgresql.JSONB),
        sa.Column("lexware_id", sa.String(64)),
        sa.Column("website", sa.String(255)),
        sa.Column("notes", sa.Text),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column(
            "custom_fields", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_organizations_name", "organizations", ["name"])
    op.create_index("ix_organizations_lexware_id", "organizations", ["lexware_id"])

    # ----- persons
    op.create_table(
        "persons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(64)),
        sa.Column(
            "current_org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        ),
        sa.Column("linkedin_url", sa.String(255)),
        sa.Column("notes", sa.Text),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column(
            "custom_fields", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_persons_name", "persons", ["name"])
    op.create_index("ix_persons_email", "persons", ["email"])

    # ----- projects
    project_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "customer_org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "status",
            sa.Enum(name="project_status", create_type=False),
            nullable=False,
            server_default="lead",
        ),
        sa.Column("hourly_rate", sa.Numeric(10, 2)),
        sa.Column("scope", sa.Text),
        sa.Column("start_date", sa.Date),
        sa.Column("end_date", sa.Date),
        sa.Column("description", sa.Text),
        sa.Column("tags", postgresql.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column(
            "custom_fields", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_projects_name", "projects", ["name"])

    # ----- obligations
    op.create_table(
        "obligations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("recurrence", sa.String(255), nullable=False),
        sa.Column("lead_time_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("action", sa.Text, nullable=False),
        sa.Column("tool", sa.String(255), nullable=False),
        sa.Column(
            "mandatory", sa.Boolean, nullable=False, server_default=sa.text("false")
        ),
        sa.Column("mandatory_label", sa.String(255)),
        sa.Column("estimated_minutes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("penalty", sa.Text),
        sa.Column("skip_if", sa.Text),
        sa.Column("anchor_date_field", sa.String(128)),
        sa.Column("raw", postgresql.JSONB, nullable=False),
    )
    op.create_index("ix_obligations_category", "obligations", ["category"])

    # ----- obligation_instances
    instance_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "obligation_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "obligation_id",
            sa.String(64),
            sa.ForeignKey("obligations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("due_date", sa.Date, nullable=False),
        sa.Column(
            "status",
            sa.Enum(name="obligation_instance_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("notified_at", sa.DateTime(timezone=True)),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("telegram_message_id", sa.BigInteger),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "obligation_id", "due_date", name="uq_obligation_instance_id_date"
        ),
    )
    op.create_index("ix_obligation_instances_obligation_id", "obligation_instances", ["obligation_id"])
    op.create_index("ix_obligation_instances_due_date", "obligation_instances", ["due_date"])

    # ----- tasks
    task_status.create(op.get_bind(), checkfirst=True)
    task_source.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("due_date", sa.Date, index=True),
        sa.Column(
            "status",
            sa.Enum(name="task_status", create_type=False),
            nullable=False,
            server_default="todo",
        ),
        sa.Column("priority", sa.Integer, nullable=False, server_default="3"),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "obligation_instance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("obligation_instances.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "source",
            sa.Enum(name="task_source", create_type=False),
            nullable=False,
            server_default="manual",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("priority BETWEEN 1 AND 5", name="ck_task_priority_range"),
    )

    # ----- notification_log
    op.create_table(
        "notification_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "obligation_instance_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("obligation_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lead_time_label", sa.String(32), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "obligation_instance_id", "lead_time_label", name="uq_notify_instance_label"
        ),
    )
    op.create_index(
        "ix_notification_log_obligation_instance_id",
        "notification_log",
        ["obligation_instance_id"],
    )

    # ----- anchor_dates
    op.create_table(
        "anchor_dates",
        sa.Column("field_name", sa.String(128), primary_key=True),
        sa.Column("date_value", sa.Date, nullable=False),
        sa.Column(
            "set_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("set_by", sa.String(64), nullable=False, server_default="user"),
    )

    # ----- pause_state (singleton)
    op.create_table(
        "pause_state",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("paused_until", sa.DateTime(timezone=True)),
        sa.CheckConstraint("id = 1", name="ck_pause_state_singleton"),
    )

    # ----- adhoc_rules (singleton)
    op.create_table(
        "adhoc_rules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "payload", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.CheckConstraint("id = 1", name="ck_adhoc_rules_singleton"),
    )

    # ----- audit_log
    audit_actor.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "actor",
            sa.Enum(name="audit_actor", create_type=False),
            nullable=False,
        ),
        sa.Column("action", sa.String(128), nullable=False),
        sa.Column("entity_type", sa.String(64)),
        sa.Column("entity_id", sa.String(64)),
        sa.Column(
            "payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_entity_type", "audit_log", ["entity_type"])
    op.create_index("ix_audit_log_entity_id", "audit_log", ["entity_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index("ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"])

    # ----- stub tables (future phases extend these in-place)
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(32), nullable=False, server_default="telegram"),
        sa.Column("external_id", sa.String(128)),
        sa.Column("subject", sa.String(255)),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(128)),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("booked_at", sa.DateTime(timezone=True)),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(8)),
        sa.Column("counterparty", sa.String(255)),
        sa.Column("reference", sa.String(255)),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lexware_id", sa.String(64)),
        sa.Column("number", sa.String(64)),
        sa.Column(
            "customer_org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        ),
        sa.Column("issued_on", sa.Date),
        sa.Column("due_on", sa.Date),
        sa.Column("total", sa.Numeric(12, 2)),
        sa.Column("status", sa.String(32)),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )
    op.create_index("ix_invoices_lexware_id", "invoices", ["lexware_id"])

    op.create_table(
        "receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vendor", sa.String(255)),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("captured_on", sa.Date),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )

    op.create_table(
        "events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(255)),
        sa.Column("title", sa.String(255)),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )

    op.create_table(
        "knowledge_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255)),
        sa.Column("body", sa.Text),
        sa.Column("source", sa.String(128)),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )

    op.create_table(
        "reading_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("title", sa.String(512)),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "medical_bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(255)),
        sa.Column("amount", sa.Numeric(12, 2)),
        sa.Column("received_on", sa.Date),
        sa.Column("status", sa.String(32)),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )

    op.create_table(
        "provider_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("encrypted_blob", sa.LargeBinary),
        sa.Column(
            "metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.UniqueConstraint(
            "tenant_id", "provider", name="uq_provider_credential_tenant_provider"
        ),
    )


def downgrade() -> None:
    op.drop_table("provider_credentials")
    op.drop_table("medical_bills")
    op.drop_table("reading_items")
    op.drop_table("knowledge_items")
    op.drop_table("events")
    op.drop_table("receipts")
    op.drop_index("ix_invoices_lexware_id", table_name="invoices")
    op.drop_table("invoices")
    op.drop_table("transactions")
    op.drop_table("documents")
    op.drop_table("messages")
    op.drop_table("conversations")
    for ix in (
        "ix_audit_log_entity",
        "ix_audit_log_created_at",
        "ix_audit_log_entity_id",
        "ix_audit_log_entity_type",
        "ix_audit_log_action",
    ):
        op.drop_index(ix, table_name="audit_log")
    op.drop_table("audit_log")
    op.execute("DROP TYPE IF EXISTS audit_actor")
    op.drop_table("adhoc_rules")
    op.drop_table("pause_state")
    op.drop_table("anchor_dates")
    op.drop_index(
        "ix_notification_log_obligation_instance_id", table_name="notification_log"
    )
    op.drop_table("notification_log")
    op.drop_table("tasks")
    op.execute("DROP TYPE IF EXISTS task_source")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.drop_index("ix_obligation_instances_due_date", table_name="obligation_instances")
    op.drop_index(
        "ix_obligation_instances_obligation_id", table_name="obligation_instances"
    )
    op.drop_table("obligation_instances")
    op.execute("DROP TYPE IF EXISTS obligation_instance_status")
    op.drop_index("ix_obligations_category", table_name="obligations")
    op.drop_table("obligations")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_table("projects")
    op.execute("DROP TYPE IF EXISTS project_status")
    op.drop_index("ix_persons_email", table_name="persons")
    op.drop_index("ix_persons_name", table_name="persons")
    op.drop_table("persons")
    op.drop_index("ix_organizations_lexware_id", table_name="organizations")
    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_table("organizations")
