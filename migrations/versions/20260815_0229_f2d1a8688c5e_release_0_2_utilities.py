"""release_0_2_utilities

Revision ID: f2d1a8688c5e
Revises: 7bab8b311cce
Create Date: 2026-08-15 02:29:23.876086+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f2d1a8688c5e'
down_revision: str | None = '7bab8b311cce'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create utility_configs table
    op.create_table(
        "utility_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("rental_space_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("utility_type", sa.String(30), nullable=False),
        sa.Column("config_type", sa.String(30), nullable=False),
        sa.Column("fixed_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("rental_space_id", "utility_type", name="uq_utility_configs_rental_space_utility"),
        sa.CheckConstraint("utility_type IN ('electricity', 'water')", name="ck_utility_configs_utility_type"),
        sa.CheckConstraint("config_type IN ('no_charge', 'fixed', 'metered')", name="ck_utility_configs_config_type"),
        sa.CheckConstraint("fixed_amount IS NULL OR fixed_amount >= 0", name="ck_utility_configs_fixed_amount_non_negative"),
    )

    # Create meters table
    op.create_table(
        "meters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("rental_space_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("utility_type", sa.String(30), nullable=False),
        sa.Column("identifier", sa.String(100), nullable=False),
        sa.Column("installation_date", sa.Date, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("rental_space_id", "utility_type", "identifier", name="uq_meters_rental_space_utility_identifier"),
        sa.CheckConstraint("utility_type IN ('electricity', 'water')", name="ck_meters_utility_type"),
    )
    op.create_index("ix_meters_rental_space_id", "meters", ["rental_space_id"])
    op.create_index("ix_meters_utility_type", "meters", ["utility_type"])
    op.create_index("ix_meters_is_active", "meters", ["is_active"])

    # Create meter_readings table
    op.create_table(
        "meter_readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("meter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reading_date", sa.Date, nullable=False),
        sa.Column("value", sa.Numeric(14, 3), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("meter_id", "reading_date", name="uq_meter_readings_meter_date"),
        sa.CheckConstraint("value >= 0", name="ck_meter_readings_value_non_negative"),
    )
    op.create_index("ix_meter_readings_meter_id", "meter_readings", ["meter_id"])
    op.create_index("ix_meter_readings_reading_date", "meter_readings", ["reading_date"])

    # Create utility_tariffs table
    op.create_table(
        "utility_tariffs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("utility_type", sa.String(30), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("utility_type", "effective_from", name="uq_utility_tariffs_utility_effective_from"),
        sa.CheckConstraint("utility_type IN ('electricity', 'water')", name="ck_utility_tariffs_utility_type"),
        sa.CheckConstraint("rate >= 0", name="ck_utility_tariffs_rate_non_negative"),
    )
    op.create_index("ix_utility_tariffs_utility_type", "utility_tariffs", ["utility_type"])
    op.create_index("ix_utility_tariffs_effective_from", "utility_tariffs", ["effective_from"])

    # Create meter_replacements table
    op.create_table(
        "meter_replacements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=sa.text("gen_random_uuid()")),
        sa.Column("old_meter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("new_meter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("replaced_on", sa.Date, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_meter_replacements_old_meter_id", "meter_replacements", ["old_meter_id"])
    op.create_index("ix_meter_replacements_new_meter_id", "meter_replacements", ["new_meter_id"])


def downgrade() -> None:
    op.drop_table("meter_replacements")
    op.drop_table("utility_tariffs")
    op.drop_table("meter_readings")
    op.drop_table("meters")
    op.drop_table("utility_configs")
