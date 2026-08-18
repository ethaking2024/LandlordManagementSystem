from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.core.exceptions import BackupError
from app.domain.enums import ExpenseCategory, PaymentMethod, SpaceType, UtilityType
from app.domain.value_objects import Money

INTEGRITY_TABLES = [
    "owners",
    "properties",
    "rental_spaces",
    "tenants",
    "agreements",
    "utility_configs",
    "meters",
    "meter_readings",
    "utility_tariffs",
    "meter_replacements",
    "bills",
    "bill_lines",
    "payments",
    "payment_allocations",
    "deposits",
    "deposit_settlements",
    "deposit_deductions",
    "expenses",
]

AGGREGATE_QUERIES = [
    ("SELECT COALESCE(SUM(amount), 0) FROM bill_lines", "bill_lines_amount"),
    ("SELECT COALESCE(SUM(amount), 0) FROM payments", "payments_amount"),
    ("SELECT COALESCE(SUM(amount), 0) FROM expenses", "expenses_amount"),
    ("SELECT COALESCE(SUM(amount), 0) FROM deposits", "deposits_amount"),
    ("SELECT COALESCE(SUM(allocated_amount), 0) FROM payment_allocations", "allocated_amount"),
]


@pytest.fixture
def backup_service(database, tmp_path):
    from app.application.services.backup_service import BackupService
    from app.infrastructure.backup import PostgresBackup

    tool = PostgresBackup(url=database.engine.url)
    return BackupService(tool, tmp_path / "backups")


def _row_counts(database) -> dict[str, int]:
    with database.engine.connect() as conn:
        return {
            table: conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            for table in INTEGRITY_TABLES
        }


def _aggregates(database) -> dict[str, object]:
    with database.engine.connect() as conn:
        return {name: conn.execute(text(query)).scalar() for query, name in AGGREGATE_QUERIES}


def _truncate_all(database) -> None:
    with database.engine.begin() as conn:
        conn.execute(
            text("TRUNCATE TABLE " + ", ".join(INTEGRITY_TABLES) + " RESTART IDENTITY CASCADE")
        )


def _seed(services) -> None:
    owner = services.owner().create_owner(name="Backup Owner", phone="9800000001")
    prop = services.property().create_property(owner.id, "Backup Building", "Kathmandu")
    space = services.rental_space().create_rental_space(prop.id, "Room 1", SpaceType.ROOM)
    tenant = services.tenant().create_tenant("Backup Tenant", "9800000002")
    agreement = services.agreement().create_agreement(
        tenant.id, space.id, date(2026, 1, 1), "25000"
    )
    services.utility_config().set_config(space.id, UtilityType.ELECTRICITY, "fixed", "1500")
    services.utility_config().set_config(space.id, UtilityType.WATER, "no_charge")

    bill = services.billing().generate_bill(
        agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31)
    )
    services.billing().confirm_bill(bill.id)

    payment = services.payment().record_payment(
        tenant.id, date(2026, 1, 31), Money(Decimal("28000")), PaymentMethod.CASH
    )
    services.payment().allocate_payment(payment.id, bill.id, Money(Decimal("26500")))

    services.deposit().record_deposit(agreement.id, Money(Decimal("50000")), date(2026, 1, 1))
    services.expense().record_expense(
        prop.id, date(2026, 1, 5), ExpenseCategory.ELECTRICAL, Money(Decimal("1200")), "Fix wiring"
    )


@pytest.mark.integration
def test_backup_restore_round_trip_preserves_data(database, backup_service, run_with_services):
    """Critical data-recovery scenario: backup survives and restore recovers it exactly."""
    run_with_services(_seed)

    before_counts = _row_counts(database)
    before_aggregates = _aggregates(database)
    assert before_counts["bills"] == 1
    assert before_counts["payment_allocations"] == 1
    assert before_aggregates["bill_lines_amount"] == Decimal("26500.00")

    backup = backup_service.create_backup()
    assert backup.path.is_file()
    assert backup.path.stat().st_size > 0
    assert backup.path.suffix == ".dump"
    assert backup_service.verify_backup(backup.path).valid

    # Simulate total data loss.
    _truncate_all(database)
    assert _row_counts(database)["bills"] == 0

    backup_service.restore_backup(backup.path)

    assert _row_counts(database) == before_counts
    assert _aggregates(database) == before_aggregates


@pytest.mark.integration
def test_backup_listing_and_multiple_backups(database, backup_service, run_with_services):
    run_with_services(_seed)
    backup_service.create_backup()
    backup_service.create_backup()

    files = backup_service.list_backups()
    assert len(files) == 2
    mtimes = [path.stat().st_mtime for path in files]
    assert mtimes == sorted(mtimes, reverse=True)


@pytest.mark.integration
def test_restore_rejects_invalid_backup_file(database, backup_service, tmp_path):
    bad = tmp_path / "not-a-backup.dump"
    bad.write_text("this is not a postgres dump archive", encoding="utf-8")

    assert backup_service.verify_backup(bad).valid is False
    with pytest.raises(BackupError, match="could not be verified"):
        backup_service.restore_backup(bad)


@pytest.mark.integration
def test_backup_service_database_name_matches(database, backup_service):
    with database.engine.connect() as conn:
        actual = conn.execute(text("SELECT current_database()")).scalar()
    assert backup_service.database_name == actual
    assert actual == "landlord_test"
