from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Expense
from app.domain.enums import ExpenseCategory, ExpenseStatus
from app.domain.value_objects import Money
from app.infrastructure.repositories import (
    ExpenseRepository,
    PropertyRepository,
    RentalSpaceRepository,
)


class ExpenseService:
    """Records landlord expenses and calculates expense totals.

    Expenses are money paid out by the landlord. They are never automatically
    charged to a tenant and never converted into bills. Voided expenses remain
    in history but are excluded from expense totals. All validation happens
    before anything is persisted.
    """

    def __init__(
        self,
        expense_repository: ExpenseRepository,
        property_repository: PropertyRepository,
        rental_space_repository: RentalSpaceRepository,
    ) -> None:
        self._expense_repository = expense_repository
        self._property_repository = property_repository
        self._rental_space_repository = rental_space_repository

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------

    def record_expense(
        self,
        property_id: uuid.UUID,
        expense_date: date,
        category: ExpenseCategory,
        amount: Money,
        description: str | None = None,
        rental_space_id: uuid.UUID | None = None,
        reference: str | None = None,
    ) -> Expense:
        property_obj = self._property_repository.get(property_id)
        if not property_obj:
            raise NotFoundError(f"Property with id {property_id} not found")

        if not isinstance(category, ExpenseCategory):
            raise ValidationError(f"Invalid expense category: {category}")

        if not isinstance(amount, Money):
            raise ValidationError("Expense amount must be a Money object")
        if amount.amount <= 0:
            raise ValidationError("Expense amount must be greater than zero")

        if rental_space_id is not None:
            rental_space = self._rental_space_repository.get(rental_space_id)
            if not rental_space:
                raise NotFoundError(f"Rental space with id {rental_space_id} not found")
            if rental_space.property_id != property_id:
                raise ValidationError(
                    f"Rental space {rental_space_id} does not belong to property {property_id}"
                )

        expense = Expense(
            property_id=property_id,
            rental_space_id=rental_space_id,
            expense_date=expense_date,
            category=category,
            amount=amount,
            description=description.strip() if description else None,
            reference=reference.strip() if reference else None,
        )
        return self._expense_repository.add(expense)

    def get_expense(self, expense_id: uuid.UUID) -> Expense:
        expense = self._expense_repository.get(expense_id)
        if not expense:
            raise NotFoundError(f"Expense with id {expense_id} not found")
        return expense

    def get_all_expenses(self, limit: int = 100, offset: int = 0) -> list[Expense]:
        return self._expense_repository.get_all(limit=limit, offset=offset)

    def get_expenses_by_property(self, property_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Expense]:
        return self._expense_repository.get_by_property(property_id, limit=limit, offset=offset)

    def get_expenses_by_rental_space(self, rental_space_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Expense]:
        return self._expense_repository.get_by_rental_space(rental_space_id, limit=limit, offset=offset)

    def get_expenses_by_date_range(
        self, start_date: date, end_date: date, limit: int = 10000, offset: int = 0
    ) -> list[Expense]:
        return self._expense_repository.get_by_date_range(start_date, end_date, limit=limit, offset=offset)

    def void_expense(self, expense_id: uuid.UUID) -> Expense:
        expense = self.get_expense(expense_id)
        if expense.status == ExpenseStatus.VOID:
            raise ValidationError("Expense is already void")
        expense.void()
        return self._expense_repository.update(expense)

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    def calculate_property_expense_total(self, property_id: uuid.UUID) -> Money:
        expenses = self._expense_repository.get_recorded_by_property(property_id)
        total = sum((e.amount.amount for e in expenses), Decimal("0"))
        return Money(total)

    def calculate_rental_space_expense_total(self, rental_space_id: uuid.UUID) -> Money:
        expenses = self._expense_repository.get_recorded_by_rental_space(rental_space_id)
        total = sum((e.amount.amount for e in expenses), Decimal("0"))
        return Money(total)
