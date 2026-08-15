"""release_0_5_deposits

Revision ID: 95cdc0cdc8fd
Revises: 889f2aa6f117
Create Date: 2026-08-15 14:31:32.829396+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '95cdc0cdc8fd'
down_revision: str | None = '889f2aa6f117'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create deposits table
    op.create_table(
        "deposits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("agreement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agreements.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("received_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_deposits_amount_positive"),
        sa.CheckConstraint("status IN ('held', 'settled', 'void')", name="ck_deposits_status"),
    )
    op.create_index("ix_deposits_agreement_id", "deposits", ["agreement_id"])
    op.create_index("ix_deposits_tenant_id", "deposits", ["tenant_id"])
    op.create_index("ix_deposits_status", "deposits", ["status"])
    op.create_index("ix_deposits_received_date", "deposits", ["received_date"])

    # Create deposit_settlements table
    op.create_table(
        "deposit_settlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("deposit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deposits.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("settlement_date", sa.Date, nullable=False),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("deposit_id", name="uq_deposit_settlements_deposit"),
        sa.CheckConstraint("refund_amount IS NULL OR refund_amount >= 0", name="ck_deposit_settlements_refund_non_negative"),
    )
    op.create_index("ix_deposit_settlements_deposit_id", "deposit_settlements", ["deposit_id"])

    # Create deposit_deductions table
    op.create_table(
        "deposit_deductions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("settlement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deposit_settlements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_deposit_deductions_amount_positive"),
    )
    op.create_index("ix_deposit_deductions_settlement_id", "deposit_deductions", ["settlement_id"])


def downgrade() -> None:
    op.drop_table("deposit_deductions")
    op.drop_table("deposit_settlements")
    op.drop_table("deposits")
