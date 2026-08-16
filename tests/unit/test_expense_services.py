from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.application.services import ExpenseService
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Expense, Property, RentalSpace
from app.domain.enums import ExpenseCategory, ExpenseStatus, SpaceType
from app.domain.value_objects import Money


def _property() -> Property:
    return Property(owner_id=uuid.uuid4(), name="Main Building", address="Kathmandu")


def _space(property_id: uuid.UUID) -> RentalSpace:
    return RentalSpace(property_id=property_id, name="Floor 1", space_type=SpaceType.FLAT)


def _recorded_expense(property_id: uuid.UUID, amount: str = "3500") -> Expense:
    return Expense(
        property_id=property_id,
        rental_space_id=uuid.uuid4(),
        expense_date=date(2026, 3, 10),
        category=ExpenseCategory.PLUMBING,
        amount=Money(Decimal(amount)),
        status=ExpenseStatus.RECORDED,
    )


class TestRecordExpense:
    @pytest.fixture
    def service(self) -> ExpenseService:
        return ExpenseService(MagicMock(), MagicMock(), MagicMock())

    def test_record_expense(self, service: ExpenseService) -> None:
        property_obj = _property()
        service._property_repository.get.return_value = property_obj
        service._expense_repository.add.side_effect = lambda e: e

        result = service.record_expense(
            property_obj.id,
            date(2026, 3, 10),
            ExpenseCategory.PLUMBING,
            Money(Decimal("3500")),
            reference="REF-1",
        )

        assert result.amount.amount == Decimal("3500.00")
        assert result.category == ExpenseCategory.PLUMBING
        assert result.status == ExpenseStatus.RECORDED
        assert result.rental_space_id is None
        service._expense_repository.add.assert_called_once()

    def test_record_property_level_expense(self, service: ExpenseService) -> None:
        property_obj = _property()
        service._property_repository.get.return_value = property_obj
        service._expense_repository.add.side_effect = lambda e: e

        result = service.record_expense(
            property_obj.id,
            date(2026, 3, 10),
            ExpenseCategory.TAX,
            Money(Decimal("20000")),
        )

        assert result.rental_space_id is None
        assert result.property_id == property_obj.id

    def test_record_rental_space_expense(self, service: ExpenseService) -> None:
        property_obj = _property()
        space = _space(property_obj.id)
        service._property_repository.get.return_value = property_obj
        service._rental_space_repository.get.return_value = space
        service._expense_repository.add.side_effect = lambda e: e

        result = service.record_expense(
            property_obj.id,
            date(2026, 3, 10),
            ExpenseCategory.PLUMBING,
            Money(Decimal("3500")),
            rental_space_id=space.id,
        )

        assert result.rental_space_id == space.id
        assert result.property_id == property_obj.id

    def test_record_expense_property_not_found(self, service: ExpenseService) -> None:
        service._property_repository.get.return_value = None
        with pytest.raises(NotFoundError, match="Property"):
            service.record_expense(
                uuid.uuid4(),
                date(2026, 3, 10),
                ExpenseCategory.TAX,
                Money(Decimal("20000")),
            )

    def test_record_expense_zero_rejected(self, service: ExpenseService) -> None:
        property_obj = _property()
        service._property_repository.get.return_value = property_obj
        with pytest.raises(ValidationError, match="greater than zero"):
            service.record_expense(
                property_obj.id,
                date(2026, 3, 10),
                ExpenseCategory.TAX,
                Money(Decimal("0")),
            )

    def test_record_expense_negative_rejected(self, service: ExpenseService) -> None:
        property_obj = _property()
        service._property_repository.get.return_value = property_obj
        with pytest.raises(ValueError, match="cannot be negative"):
            service.record_expense(
                property_obj.id,
                date(2026, 3, 10),
                ExpenseCategory.TAX,
                Money(Decimal("-5")),
            )

    def test_record_expense_invalid_category_rejected(self, service: ExpenseService) -> None:
        property_obj = _property()
        service._property_repository.get.return_value = property_obj
        with pytest.raises(ValidationError, match="Invalid expense category"):
            service.record_expense(
                property_obj.id,
                date(2026, 3, 10),
                "repairs",
                Money(Decimal("3500")),
            )


class TestRentalSpaceValidation:
    @pytest.fixture
    def service(self) -> ExpenseService:
        return ExpenseService(MagicMock(), MagicMock(), MagicMock())

    def test_rental_space_must_belong_to_property(self, service: ExpenseService) -> None:
        property_obj = _property()
        other_property_id = uuid.uuid4()
        space = _space(other_property_id)
        service._property_repository.get.return_value = property_obj
        service._rental_space_repository.get.return_value = space

        with pytest.raises(ValidationError, match="does not belong to property"):
            service.record_expense(
                property_obj.id,
                date(2026, 3, 10),
                ExpenseCategory.PLUMBING,
                Money(Decimal("3500")),
                rental_space_id=space.id,
            )

    def test_rental_space_not_found(self, service: ExpenseService) -> None:
        property_obj = _property()
        service._property_repository.get.return_value = property_obj
        service._rental_space_repository.get.return_value = None

        with pytest.raises(NotFoundError, match="Rental space"):
            service.record_expense(
                property_obj.id,
                date(2026, 3, 10),
                ExpenseCategory.PLUMBING,
                Money(Decimal("3500")),
                rental_space_id=uuid.uuid4(),
            )


class TestVoidExpense:
    @pytest.fixture
    def service(self) -> ExpenseService:
        return ExpenseService(MagicMock(), MagicMock(), MagicMock())

    def test_void_expense(self, service: ExpenseService) -> None:
        property_obj = _property()
        expense = _recorded_expense(property_obj.id)
        service._expense_repository.get.return_value = expense
        service._expense_repository.update.side_effect = lambda e: e

        result = service.void_expense(expense.id)

        assert result.status == ExpenseStatus.VOID
        service._expense_repository.update.assert_called_once()

    def test_void_twice_rejected(self, service: ExpenseService) -> None:
        property_obj = _property()
        expense = _recorded_expense(property_obj.id)
        expense.void()
        service._expense_repository.get.return_value = expense

        with pytest.raises(ValidationError, match="already void"):
            service.void_expense(expense.id)

    def test_void_expense_historical_record_remains(self, service: ExpenseService) -> None:
        property_obj = _property()
        expense = _recorded_expense(property_obj.id)
        service._expense_repository.get.return_value = expense
        service._expense_repository.update.side_effect = lambda e: e

        result = service.void_expense(expense.id)

        # The expense is not deleted; it is only transitioned to VOID.
        assert result.id is not None
        assert result.status == ExpenseStatus.VOID

    def test_void_expense_not_found(self, service: ExpenseService) -> None:
        service._expense_repository.get.return_value = None
        with pytest.raises(NotFoundError, match="Expense"):
            service.void_expense(uuid.uuid4())


class TestTotals:
    @pytest.fixture
    def service(self) -> ExpenseService:
        return ExpenseService(MagicMock(), MagicMock(), MagicMock())

    def test_property_total_sums_recorded(self, service: ExpenseService) -> None:
        property_obj = _property()
        e1 = _recorded_expense(property_obj.id, "10000")
        e2 = _recorded_expense(property_obj.id, "3500")
        service._expense_repository.get_recorded_by_property.return_value = [e1, e2]

        total = service.calculate_property_expense_total(property_obj.id)

        assert total.amount == Decimal("13500.00")

    def test_property_total_excludes_voided(self, service: ExpenseService) -> None:
        property_obj = _property()
        e1 = _recorded_expense(property_obj.id, "10000")
        e2 = _recorded_expense(property_obj.id, "3500")
        e2.void()
        service._expense_repository.get_recorded_by_property.return_value = [e1]

        total = service.calculate_property_expense_total(property_obj.id)

        assert total.amount == Decimal("10000.00")

    def test_rental_space_total_sums_recorded(self, service: ExpenseService) -> None:
        property_obj = _property()
        space_id = uuid.uuid4()
        e1 = _recorded_expense(property_obj.id, "3500")
        e2 = _recorded_expense(property_obj.id, "1500")
        service._expense_repository.get_recorded_by_rental_space.return_value = [e1, e2]

        total = service.calculate_rental_space_expense_total(space_id)

        assert total.amount == Decimal("5000.00")

    def test_rental_space_total_excludes_voided(self, service: ExpenseService) -> None:
        property_obj = _property()
        e1 = _recorded_expense(property_obj.id, "3500")
        e2 = _recorded_expense(property_obj.id, "1500")
        e2.void()
        service._expense_repository.get_recorded_by_rental_space.return_value = [e1]

        total = service.calculate_rental_space_expense_total(uuid.uuid4())

        assert total.amount == Decimal("3500.00")

    def test_empty_total_is_zero(self, service: ExpenseService) -> None:
        service._expense_repository.get_recorded_by_property.return_value = []

        total = service.calculate_property_expense_total(uuid.uuid4())

        assert total.amount == Decimal("0.00")


class TestMoney:
    @pytest.fixture
    def service(self) -> ExpenseService:
        return ExpenseService(MagicMock(), MagicMock(), MagicMock())

    def test_decimal_two_decimals(self, service: ExpenseService) -> None:
        property_obj = _property()
        service._property_repository.get.return_value = property_obj
        service._expense_repository.add.side_effect = lambda e: e

        result = service.record_expense(
            property_obj.id,
            date(2026, 3, 10),
            ExpenseCategory.TAX,
            Money(Decimal("20000.006")),
        )

        assert result.amount.amount == Decimal("20000.01")
        assert isinstance(result.amount.amount, Decimal)

    def test_total_is_decimal_not_float(self, service: ExpenseService) -> None:
        property_obj = _property()
        e1 = _recorded_expense(property_obj.id, "10000")
        e2 = _recorded_expense(property_obj.id, "3500.006")
        service._expense_repository.get_recorded_by_property.return_value = [e1, e2]

        total = service.calculate_property_expense_total(property_obj.id)

        assert isinstance(total.amount, Decimal)
        assert total.amount == Decimal("13500.01")


class TestGetAllExpenses:
    @pytest.fixture
    def service(self) -> ExpenseService:
        return ExpenseService(MagicMock(), MagicMock(), MagicMock())

    def test_get_all_expenses_delegates_to_repository(self, service: ExpenseService) -> None:
        property_obj = _property()
        expected = [_recorded_expense(property_obj.id, "3500")]
        service._expense_repository.get_all.return_value = expected

        result = service.get_all_expenses(limit=50, offset=10)

        assert result == expected
        service._expense_repository.get_all.assert_called_once_with(limit=50, offset=10)


class TestGetExpensesByDateRange:
    @pytest.fixture
    def service(self) -> ExpenseService:
        return ExpenseService(MagicMock(), MagicMock(), MagicMock())

    def test_delegates_to_repository(self, service: ExpenseService) -> None:
        property_obj = _property()
        expected = [_recorded_expense(property_obj.id, "3500")]
        service._expense_repository.get_by_date_range.return_value = expected

        result = service.get_expenses_by_date_range(date(2026, 1, 1), date(2026, 1, 31))

        service._expense_repository.get_by_date_range.assert_called_once_with(
            date(2026, 1, 1), date(2026, 1, 31), limit=10000, offset=0
        )
        assert result == expected

    def test_empty_range(self, service: ExpenseService) -> None:
        service._expense_repository.get_by_date_range.return_value = []

        result = service.get_expenses_by_date_range(date(2026, 1, 1), date(2026, 1, 31))

        assert result == []


class TestTransactionSafety:
    @pytest.fixture
    def service(self) -> ExpenseService:
        return ExpenseService(MagicMock(), MagicMock(), MagicMock())

    def test_failed_record_persists_nothing(self, service: ExpenseService) -> None:
        property_obj = _property()
        service._property_repository.get.return_value = property_obj

        with pytest.raises(ValidationError, match="does not belong to property"):
            service.record_expense(
                property_obj.id,
                date(2026, 3, 10),
                ExpenseCategory.PLUMBING,
                Money(Decimal("3500")),
                rental_space_id=uuid.uuid4(),
            )

        # Validation fails before any expense is committed.
        service._expense_repository.add.assert_not_called()

    def test_failed_record_invalid_category_persists_nothing(self, service: ExpenseService) -> None:
        property_obj = _property()
        service._property_repository.get.return_value = property_obj

        with pytest.raises(ValidationError, match="Invalid expense category"):
            service.record_expense(
                property_obj.id,
                date(2026, 3, 10),
                "repairs",
                Money(Decimal("3500")),
            )

        service._expense_repository.add.assert_not_called()
