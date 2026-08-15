"""release_0_3_billing

Revision ID: f77d7a576735
Revises: f2d1a8688c5e
Create Date: 2026-08-15 04:34:13.294344+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f77d7a576735'
down_revision: str | None = 'f2d1a8688c5e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create bills table
    op.create_table(
        "bills",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("agreement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agreements.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rental_space_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("billing_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("agreement_id", "period_start", "period_end", name="uq_bills_agreement_period"),
        sa.CheckConstraint("period_end >= period_start", name="ck_bills_period_end_after_start"),
        sa.CheckConstraint("total_amount >= 0", name="ck_bills_total_non_negative"),
        sa.CheckConstraint("status IN ('draft', 'confirmed', 'void')", name="ck_bills_status"),
    )
    op.create_index("ix_bills_agreement_id", "bills", ["agreement_id"])
    op.create_index("ix_bills_tenant_id", "bills", ["tenant_id"])
    op.create_index("ix_bills_rental_space_id", "bills", ["rental_space_id"])
    op.create_index("ix_bills_status", "bills", ["status"])
    op.create_index("ix_bills_period_start", "bills", ["period_start"])

    # Create bill_lines table
    op.create_table(
        "bill_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("quantity", sa.Numeric(18, 3), nullable=True),
        sa.Column("unit_rate", sa.Numeric(12, 2), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("config_type", sa.String(30), nullable=True),
        sa.Column("meter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meters.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("meter_identifier", sa.String(100), nullable=True),
        sa.Column("previous_reading", sa.Numeric(18, 3), nullable=True),
        sa.Column("current_reading", sa.Numeric(18, 3), nullable=True),
        sa.Column("consumption", sa.Numeric(18, 3), nullable=True),
        sa.Column("tariff_rate", sa.Numeric(12, 2), nullable=True),
        sa.Column("tariff_effective_from", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount >= 0", name="ck_bill_lines_amount_non_negative"),
        sa.CheckConstraint("category IN ('rent', 'electricity', 'water')", name="ck_bill_lines_category"),
    )
    op.create_index("ix_bill_lines_bill_id", "bill_lines", ["bill_id"])
    op.create_index("ix_bill_lines_category", "bill_lines", ["category"])
    op.create_index("ix_bill_lines_meter_id", "bill_lines", ["meter_id"])


def downgrade() -> None:
    op.drop_table("bill_lines")
    op.drop_table("bills")
