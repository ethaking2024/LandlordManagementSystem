"""release_0_4_payments

Revision ID: 889f2aa6f117
Revises: f77d7a576735
Create Date: 2026-08-15 14:06:25.669424+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '889f2aa6f117'
down_revision: str | None = 'f77d7a576735'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create payments table
    op.create_table(
        "payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_date", sa.Date, nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_method", sa.String(30), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.CheckConstraint("payment_method IN ('cash', 'bank_transfer', 'online', 'other')", name="ck_payments_payment_method"),
        sa.CheckConstraint("status IN ('recorded', 'void')", name="ck_payments_status"),
    )
    op.create_index("ix_payments_tenant_id", "payments", ["tenant_id"])
    op.create_index("ix_payments_payment_date", "payments", ["payment_date"])
    op.create_index("ix_payments_status", "payments", ["status"])

    # Create payment_allocations table
    op.create_table(
        "payment_allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("payment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("bill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bills.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("allocated_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("payment_id", "bill_id", name="uq_payment_allocations_payment_bill"),
        sa.CheckConstraint("allocated_amount > 0", name="ck_payment_allocations_amount_positive"),
    )
    op.create_index("ix_payment_allocations_payment_id", "payment_allocations", ["payment_id"])
    op.create_index("ix_payment_allocations_bill_id", "payment_allocations", ["bill_id"])


def downgrade() -> None:
    op.drop_table("payment_allocations")
    op.drop_table("payments")
