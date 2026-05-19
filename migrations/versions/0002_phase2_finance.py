"""phase 2 — extend invoice/receipt/transaction stubs + add finance tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-19 00:00:00

"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEED_EXPENSES: list[dict[str, object]] = [
    {
        "name": "Claude subscription",
        "amount": Decimal("18.00"),
        "cadence": "monthly",
    },
    {
        "name": "Lebara mobile",
        "amount": Decimal("3.99"),
        "cadence": "monthly",
    },
    {
        "name": "Lexware Office",
        "amount": Decimal("19.57"),
        "cadence": "monthly",
        "next_amount": Decimal("32.90"),
        "next_amount_effective_from": date(2026, 8, 2),
    },
    {
        "name": "Google Workspace",
        "amount": Decimal("8.10"),
        "cadence": "monthly",
    },
    {
        "name": "Hetzner",
        "amount": Decimal("5.65"),
        "cadence": "monthly",
    },
]

DEFAULT_TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")


def upgrade() -> None:
    invoice_status = sa.Enum(
        "draft", "open", "paid", "overdue", "cancelled", name="invoice_status"
    )
    receipt_status = sa.Enum("pending", "matched", "missing", name="receipt_status")
    transaction_status = sa.Enum(
        "unmatched", "matched", "ignored", name="transaction_status"
    )
    transaction_direction = sa.Enum("in", "out", name="transaction_direction")
    expense_cadence = sa.Enum("monthly", "quarterly", "yearly", name="expense_cadence")
    ustva_status = sa.Enum(
        "preparing", "review", "approved", "submitted", name="ustva_status"
    )
    invoice_status.create(op.get_bind(), checkfirst=True)
    receipt_status.create(op.get_bind(), checkfirst=True)
    transaction_status.create(op.get_bind(), checkfirst=True)
    transaction_direction.create(op.get_bind(), checkfirst=True)
    expense_cadence.create(op.get_bind(), checkfirst=True)
    ustva_status.create(op.get_bind(), checkfirst=True)

    # ----- extend invoices ------------------------------------------------
    op.add_column("invoices", sa.Column("project_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key(
        "fk_invoices_project_id",
        "invoices",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("invoices", "issued_on", new_column_name="issue_date")
    op.alter_column("invoices", "due_on", new_column_name="due_date")
    op.alter_column("invoices", "total", new_column_name="total_gross")
    op.add_column("invoices", sa.Column("total_net", sa.Numeric(12, 2)))
    op.add_column(
        "invoices",
        sa.Column("currency", sa.String(8), nullable=False, server_default="EUR"),
    )
    op.add_column("invoices", sa.Column("paid_date", sa.Date))
    op.add_column(
        "invoices",
        sa.Column("mahnstufe", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column("invoices", sa.Column("last_mahnung_at", sa.DateTime(timezone=True)))
    op.add_column(
        "invoices",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "invoices",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.execute("UPDATE invoices SET status = 'draft' WHERE status IS NULL")
    op.alter_column(
        "invoices",
        "status",
        existing_type=sa.String(32),
        type_=postgresql.ENUM(name="invoice_status", create_type=False),
        postgresql_using="status::invoice_status",
        nullable=False,
        server_default="draft",
    )
    op.create_index("ix_invoices_due_date", "invoices", ["due_date"])

    # ----- extend receipts ------------------------------------------------
    op.add_column("receipts", sa.Column("lexware_id", sa.String(64)))
    op.create_index("ix_receipts_lexware_id", "receipts", ["lexware_id"])
    op.add_column("receipts", sa.Column("vendor_org_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key(
        "fk_receipts_vendor_org_id",
        "receipts",
        "organizations",
        ["vendor_org_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("receipts", sa.Column("project_id", postgresql.UUID(as_uuid=True)))
    op.create_foreign_key(
        "fk_receipts_project_id",
        "receipts",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("receipts", "captured_on", new_column_name="date")
    op.alter_column("receipts", "amount", new_column_name="total")
    op.add_column("receipts", sa.Column("vat", sa.Numeric(12, 2)))
    op.add_column("receipts", sa.Column("category", sa.String(64)))
    op.add_column(
        "receipts",
        sa.Column(
            "status",
            postgresql.ENUM(name="receipt_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "receipts",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "receipts",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.drop_column("receipts", "vendor")
    op.create_index("ix_receipts_date", "receipts", ["date"])

    # ----- extend transactions -------------------------------------------
    op.add_column("transactions", sa.Column("account", sa.String(64)))
    op.add_column("transactions", sa.Column("lexware_match_id", sa.String(64)))
    op.add_column(
        "transactions", sa.Column("project_id", postgresql.UUID(as_uuid=True))
    )
    op.create_foreign_key(
        "fk_transactions_project_id",
        "transactions",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "transactions",
        sa.Column(
            "status",
            postgresql.ENUM(name="transaction_status", create_type=False),
            nullable=False,
            server_default="unmatched",
        ),
    )
    op.add_column(
        "transactions",
        sa.Column(
            "direction",
            postgresql.ENUM(name="transaction_direction", create_type=False),
        ),
    )

    # ----- recurring_expenses --------------------------------------------
    op.create_table(
        "recurring_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="EUR"),
        sa.Column(
            "cadence",
            postgresql.ENUM(name="expense_cadence", create_type=False),
            nullable=False,
            server_default="monthly",
        ),
        sa.Column(
            "vendor_org_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
        ),
        sa.Column("category", sa.String(64)),
        sa.Column("vat_rate", sa.Numeric(5, 2)),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("effective_from", sa.Date),
        sa.Column("effective_until", sa.Date),
        sa.Column("next_amount", sa.Numeric(12, 2)),
        sa.Column("next_amount_effective_from", sa.Date),
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

    # ----- time_entries ---------------------------------------------------
    op.create_table(
        "time_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("date", sa.Date, nullable=False, index=True),
        sa.Column("hours", sa.Numeric(6, 2), nullable=False),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
        ),
        sa.Column("note", sa.Text),
        sa.Column("billable", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("billed", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
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

    # ----- vat_validations -----------------------------------------------
    op.create_table(
        "vat_validations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("vat_id_queried", sa.String(32), nullable=False, index=True),
        sa.Column("requester_vat_id", sa.String(32)),
        sa.Column("valid", sa.Boolean, nullable=False),
        sa.Column("name_match", sa.String(16)),
        sa.Column("address_match", sa.String(16)),
        sa.Column("consultation_number", sa.String(64)),
        sa.Column(
            "raw_response",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="SET NULL"),
        ),
        sa.Column("pdf_storage_key", sa.String(512)),
        sa.Column(
            "queried_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ----- ustva_periods --------------------------------------------------
    op.create_table(
        "ustva_periods",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("quarter", sa.Integer, nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="ustva_status", create_type=False),
            nullable=False,
            server_default="preparing",
        ),
        sa.Column(
            "payload",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "missing_receipts",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("preview_sent_at", sa.DateTime(timezone=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "tenant_id", "year", "quarter", name="uq_ustva_tenant_year_quarter"
        ),
        sa.CheckConstraint("quarter BETWEEN 1 AND 4", name="ck_ustva_quarter_range"),
    )

    # ----- dunning_runs ---------------------------------------------------
    op.create_table(
        "dunning_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "invoice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("mahnstufe", sa.Integer, nullable=False),
        sa.Column("draft_text", sa.Text, nullable=False),
        sa.Column(
            "interest_amount", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column(
            "fee_amount", sa.Numeric(12, 2), nullable=False, server_default="0"
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "invoice_id", "mahnstufe", name="uq_dunning_invoice_stufe"
        ),
    )

    # ----- liquidity_snapshots -------------------------------------------
    op.create_table(
        "liquidity_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column("opening_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("runway_date", sa.Date),
        sa.Column(
            "scheduled_outflows",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "expected_inflows",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "alerts",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # ----- seed recurring expenses ---------------------------------------
    recurring_expenses = sa.table(
        "recurring_expenses",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("tenant_id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("amount", sa.Numeric()),
        sa.column("currency", sa.String()),
        sa.column("cadence", sa.String()),
        sa.column("active", sa.Boolean()),
        sa.column("next_amount", sa.Numeric()),
        sa.column("next_amount_effective_from", sa.Date()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.utcnow()
    rows = [
        {
            "id": uuid4(),
            "tenant_id": DEFAULT_TENANT_ID,
            "name": e["name"],
            "amount": e["amount"],
            "currency": "EUR",
            "cadence": e["cadence"],
            "active": True,
            "next_amount": e.get("next_amount"),
            "next_amount_effective_from": e.get("next_amount_effective_from"),
            "created_at": now,
            "updated_at": now,
        }
        for e in SEED_EXPENSES
    ]
    op.bulk_insert(recurring_expenses, rows)


def downgrade() -> None:
    op.drop_table("liquidity_snapshots")
    op.drop_table("dunning_runs")
    op.drop_table("ustva_periods")
    op.drop_table("vat_validations")
    op.drop_table("time_entries")
    op.drop_table("recurring_expenses")

    op.drop_column("transactions", "direction")
    op.drop_column("transactions", "status")
    op.drop_constraint("fk_transactions_project_id", "transactions", type_="foreignkey")
    op.drop_column("transactions", "project_id")
    op.drop_column("transactions", "lexware_match_id")
    op.drop_column("transactions", "account")

    op.drop_index("ix_receipts_date", table_name="receipts")
    op.add_column("receipts", sa.Column("vendor", sa.String(255)))
    op.drop_column("receipts", "updated_at")
    op.drop_column("receipts", "created_at")
    op.drop_column("receipts", "status")
    op.drop_column("receipts", "category")
    op.drop_column("receipts", "vat")
    op.alter_column("receipts", "total", new_column_name="amount")
    op.alter_column("receipts", "date", new_column_name="captured_on")
    op.drop_constraint("fk_receipts_project_id", "receipts", type_="foreignkey")
    op.drop_column("receipts", "project_id")
    op.drop_constraint("fk_receipts_vendor_org_id", "receipts", type_="foreignkey")
    op.drop_column("receipts", "vendor_org_id")
    op.drop_index("ix_receipts_lexware_id", table_name="receipts")
    op.drop_column("receipts", "lexware_id")

    op.drop_index("ix_invoices_due_date", table_name="invoices")
    op.alter_column(
        "invoices",
        "status",
        existing_type=postgresql.ENUM(name="invoice_status", create_type=False),
        type_=sa.String(32),
        postgresql_using="status::text",
    )
    op.drop_column("invoices", "updated_at")
    op.drop_column("invoices", "created_at")
    op.drop_column("invoices", "last_mahnung_at")
    op.drop_column("invoices", "mahnstufe")
    op.drop_column("invoices", "paid_date")
    op.drop_column("invoices", "currency")
    op.drop_column("invoices", "total_net")
    op.alter_column("invoices", "total_gross", new_column_name="total")
    op.alter_column("invoices", "due_date", new_column_name="due_on")
    op.alter_column("invoices", "issue_date", new_column_name="issued_on")
    op.drop_constraint("fk_invoices_project_id", "invoices", type_="foreignkey")
    op.drop_column("invoices", "project_id")

    op.execute("DROP TYPE IF EXISTS ustva_status")
    op.execute("DROP TYPE IF EXISTS expense_cadence")
    op.execute("DROP TYPE IF EXISTS transaction_direction")
    op.execute("DROP TYPE IF EXISTS transaction_status")
    op.execute("DROP TYPE IF EXISTS receipt_status")
    op.execute("DROP TYPE IF EXISTS invoice_status")
