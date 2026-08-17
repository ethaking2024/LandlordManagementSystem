from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from tests.integration.conftest import MODEL_TABLES


@pytest.mark.integration
def test_schema_has_exactly_one_alembic_head(database):
    with database.engine.connect() as conn:
        revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert revision == "12dce878caf4"


@pytest.mark.integration
def test_all_model_tables_exist(database):
    inspector = inspect(database.engine)
    tables = set(inspector.get_table_names())
    for name in MODEL_TABLES:
        assert name in tables, f"missing table {name}"


@pytest.mark.integration
def test_representative_foreign_keys_and_ondelete(database):
    inspector = inspect(database.engine)

    def fks(table):
        return {(fk["referred_table"], fk["options"].get("ondelete")) for fk in inspector.get_foreign_keys(table)}

    assert ("owners", "RESTRICT") in fks("properties")
    assert ("properties", "RESTRICT") in fks("rental_spaces")
    assert ("tenants", "RESTRICT") in fks("agreements")
    assert ("agreements", "RESTRICT") in fks("bills")
    assert ("bills", "CASCADE") in fks("bill_lines")
    assert ("payments", "RESTRICT") in fks("payment_allocations")
    assert ("bills", "RESTRICT") in fks("payment_allocations")
    assert ("deposits", "RESTRICT") in fks("deposit_settlements")
    assert ("deposit_settlements", "CASCADE") in fks("deposit_deductions")


@pytest.mark.integration
def test_unique_constraints_exist(database):
    inspector = inspect(database.engine)

    def uniques(table):
        return {tuple(sorted(uc["column_names"])) for uc in inspector.get_unique_constraints(table)}

    assert ("agreement_id", "period_end", "period_start") in uniques("bills")
    assert ("bill_id", "payment_id") in uniques("payment_allocations")
    assert ("deposit_id",) in uniques("deposit_settlements")
    assert ("meter_id", "reading_date") in uniques("meter_readings")
    assert ("rental_space_id", "utility_type") in uniques("utility_configs")
    assert ("effective_from", "utility_type") in uniques("utility_tariffs")
    assert ("identifier", "rental_space_id", "utility_type") in uniques("meters")


@pytest.mark.integration
def test_check_constraints_exist(database):
    inspector = inspect(database.engine)

    def checks(table):
        return {ck["name"] for ck in inspector.get_check_constraints(table)}

    assert "ck_bills_status" in checks("bills")
    assert "ck_bills_period_end_after_start" in checks("bills")
    assert "ck_payments_amount_positive" in checks("payments")
    assert "ck_payment_allocations_amount_positive" in checks("payment_allocations")
    assert "ck_deposits_amount_positive" in checks("deposits")
    assert "ck_deposit_settlements_refund_non_negative" in checks("deposit_settlements")
    assert "ck_deposit_deductions_amount_positive" in checks("deposit_deductions")
    assert "ck_expenses_amount_positive" in checks("expenses")
    assert "ck_expenses_category" in checks("expenses")
    assert "ck_meter_readings_value_non_negative" in checks("meter_readings")
    assert "ck_agreements_status" in checks("agreements")
    assert "ck_rental_spaces_space_type" in checks("rental_spaces")
