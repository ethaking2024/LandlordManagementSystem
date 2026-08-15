"""release_0_1_core_data

Revision ID: 7bab8b311cce
Revises: 0dfa548a18bd
Create Date: 2026-08-14 13:40:24.806199+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7bab8b311cce'
down_revision: str | None = '0dfa548a18bd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create owners table
    op.create_table(
        "owners",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create properties table
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("owners.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("address", sa.Text, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_properties_owner_id", "properties", ["owner_id"])

    # Create rental_spaces table
    op.create_table(
        "rental_spaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("space_type", sa.String(30), nullable=False),
        sa.Column("floor_label", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_rental_spaces_property_id", "rental_spaces", ["property_id"])
    op.create_index("ix_rental_spaces_is_active", "rental_spaces", ["is_active"])
    op.create_check_constraint(
        "ck_rental_spaces_space_type",
        "rental_spaces",
        "space_type IN ('whole_floor', 'flat', 'room', 'room_group', 'other')",
    )

    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("alternate_phone", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("address", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tenants_full_name", "tenants", ["full_name"])

    # Create agreements table
    op.create_table(
        "agreements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("rental_space_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("monthly_rent", sa.Numeric(12, 2), nullable=False, default="0"),
        sa.Column("security_deposit", sa.Numeric(12, 2), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, default="active"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agreements_tenant_id", "agreements", ["tenant_id"])
    op.create_index("ix_agreements_rental_space_id", "agreements", ["rental_space_id"])
    op.create_index("ix_agreements_status", "agreements", ["status"])
    op.create_check_constraint("ck_agreements_monthly_rent_non_negative", "agreements", "monthly_rent >= 0")
    op.create_check_constraint("ck_agreements_security_deposit_non_negative", "agreements", "security_deposit IS NULL OR security_deposit >= 0")
    op.create_check_constraint("ck_agreements_end_date_after_start", "agreements", "end_date IS NULL OR end_date >= start_date")
    op.create_check_constraint("ck_agreements_status", "agreements", "status IN ('active', 'ended', 'cancelled')")


def downgrade() -> None:
    op.drop_table("agreements")
    op.drop_table("tenants")
    op.drop_table("rental_spaces")
    op.drop_table("properties")
    op.drop_table("owners")
