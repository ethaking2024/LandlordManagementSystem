"""release_0_6_expenses

Revision ID: 12dce878caf4
Revises: 95cdc0cdc8fd
Create Date: 2026-08-15 15:48:25.810122+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '12dce878caf4'
down_revision: str | None = '95cdc0cdc8fd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create expenses table
    op.create_table(
        "expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rental_space_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("expense_date", sa.Date, nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("reference", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        sa.CheckConstraint(
            "category IN ('electrical', 'plumbing', 'cleaning', 'tax', 'common_area', 'other')",
            name="ck_expenses_category",
        ),
        sa.CheckConstraint("status IN ('recorded', 'void')", name="ck_expenses_status"),
    )
    op.create_index("ix_expenses_property_id", "expenses", ["property_id"])
    op.create_index("ix_expenses_rental_space_id", "expenses", ["rental_space_id"])
    op.create_index("ix_expenses_expense_date", "expenses", ["expense_date"])
    op.create_index("ix_expenses_category", "expenses", ["category"])
    op.create_index("ix_expenses_status", "expenses", ["status"])


def downgrade() -> None:
    op.drop_table("expenses")
