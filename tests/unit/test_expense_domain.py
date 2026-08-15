from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.domain import Expense, ExpenseCategory, ExpenseStatus
from app.domain.value_objects import Money


class TestExpense:
    def test_valid_expense(self) -> None:
        expense = Expense(
            property_id=uuid.uuid4(),
            expense_date=date(2026, 3, 10),
            category=ExpenseCategory.PLUMBING,
            amount=Money(Decimal("3500")),
        )
        assert expense.status == ExpenseStatus.RECORDED
        assert expense.is_recorded is True
        assert expense.rental_space_id is None
        assert expense.amount.amount == Decimal("3500.00")

    def test_amount_quantized_to_two_decimals(self) -> None:
        expense = Expense(
            property_id=uuid.uuid4(),
            expense_date=date(2026, 3, 10),
            category=ExpenseCategory.TAX,
            amount=Money(Decimal("20000.006")),
        )
        assert expense.amount.amount == Decimal("20000.01")

    def test_rejects_non_money_amount(self) -> None:
        with pytest.raises(ValueError, match="must be a Money object"):
            Expense(
                property_id=uuid.uuid4(),
                expense_date=date(2026, 3, 10),
                category=ExpenseCategory.TAX,
                amount=Decimal("20000"),
            )

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValueError, match="greater than zero"):
            Expense(
                property_id=uuid.uuid4(),
                expense_date=date(2026, 3, 10),
                category=ExpenseCategory.TAX,
                amount=Money(Decimal("0")),
            )

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            Expense(
                property_id=uuid.uuid4(),
                expense_date=date(2026, 3, 10),
                category=ExpenseCategory.TAX,
                amount=Money(Decimal("-5")),
            )

    def test_rejects_invalid_category(self) -> None:
        with pytest.raises(ValueError, match="Invalid expense category"):
            Expense(
                property_id=uuid.uuid4(),
                expense_date=date(2026, 3, 10),
                category="repairs",
                amount=Money(Decimal("3500")),
            )

    def test_rejects_invalid_status(self) -> None:
        with pytest.raises(ValueError, match="Invalid expense status"):
            Expense(
                property_id=uuid.uuid4(),
                expense_date=date(2026, 3, 10),
                category=ExpenseCategory.OTHER,
                amount=Money(Decimal("3500")),
                status="deleted",
            )

    def test_strips_description_and_reference(self) -> None:
        expense = Expense(
            property_id=uuid.uuid4(),
            expense_date=date(2026, 3, 10),
            category=ExpenseCategory.CLEANING,
            amount=Money(Decimal("1500")),
            description="  Common area cleaning  ",
            reference="  REF-001  ",
        )
        assert expense.description == "Common area cleaning"
        assert expense.reference == "REF-001"

    def test_rental_space_optional(self) -> None:
        expense = Expense(
            property_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            expense_date=date(2026, 3, 10),
            category=ExpenseCategory.PLUMBING,
            amount=Money(Decimal("3500")),
        )
        assert expense.rental_space_id is not None

    def test_all_categories_valid(self) -> None:
        for category in ExpenseCategory:
            expense = Expense(
                property_id=uuid.uuid4(),
                expense_date=date(2026, 3, 10),
                category=category,
                amount=Money(Decimal("1000")),
            )
            assert expense.category == category

    def test_void_sets_status(self) -> None:
        expense = Expense(
            property_id=uuid.uuid4(),
            expense_date=date(2026, 3, 10),
            category=ExpenseCategory.TAX,
            amount=Money(Decimal("20000")),
        )
        expense.void()
        assert expense.status == ExpenseStatus.VOID
        assert expense.is_recorded is False

    def test_void_twice_rejected(self) -> None:
        expense = Expense(
            property_id=uuid.uuid4(),
            expense_date=date(2026, 3, 10),
            category=ExpenseCategory.TAX,
            amount=Money(Decimal("20000")),
        )
        expense.void()
        with pytest.raises(ValueError, match="already void"):
            expense.void()
