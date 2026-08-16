from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Expense
from app.domain.enums import ExpenseCategory, ExpenseStatus
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import ExpenseModel
from app.infrastructure.repositories.base import RepositoryBase


class ExpenseRepository(RepositoryBase[Expense]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: Expense) -> Expense:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> Expense | None:
        model = self.session.get(ExpenseModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Expense]:
        stmt = select(ExpenseModel).order_by(ExpenseModel.expense_date).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_property(self, property_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Expense]:
        stmt = (
            select(ExpenseModel)
            .where(ExpenseModel.property_id == property_id)
            .order_by(ExpenseModel.expense_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_rental_space(self, rental_space_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Expense]:
        stmt = (
            select(ExpenseModel)
            .where(ExpenseModel.rental_space_id == rental_space_id)
            .order_by(ExpenseModel.expense_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_date_range(self, start: date, end: date, limit: int = 10000, offset: int = 0) -> list[Expense]:
        stmt = (
            select(ExpenseModel)
            .where(ExpenseModel.expense_date >= start, ExpenseModel.expense_date <= end)
            .order_by(ExpenseModel.expense_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_category(self, category: ExpenseCategory, limit: int = 100, offset: int = 0) -> list[Expense]:
        stmt = (
            select(ExpenseModel)
            .where(ExpenseModel.category == category.value)
            .order_by(ExpenseModel.expense_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_status(self, status: ExpenseStatus, limit: int = 100, offset: int = 0) -> list[Expense]:
        stmt = (
            select(ExpenseModel)
            .where(ExpenseModel.status == status.value)
            .order_by(ExpenseModel.expense_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_recorded_by_property(self, property_id: uuid.UUID) -> list[Expense]:
        stmt = select(ExpenseModel).where(
            ExpenseModel.property_id == property_id,
            ExpenseModel.status == ExpenseStatus.RECORDED.value,
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_recorded_by_rental_space(self, rental_space_id: uuid.UUID) -> list[Expense]:
        stmt = select(ExpenseModel).where(
            ExpenseModel.rental_space_id == rental_space_id,
            ExpenseModel.status == ExpenseStatus.RECORDED.value,
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def update(self, entity: Expense) -> Expense:
        model = self.session.get(ExpenseModel, entity.id)
        if not model:
            raise ValueError(f"Expense with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(ExpenseModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: Expense) -> ExpenseModel:
        return ExpenseModel(
            id=entity.id,
            property_id=entity.property_id,
            rental_space_id=entity.rental_space_id,
            expense_date=entity.expense_date,
            category=entity.category.value,
            amount=entity.amount.amount,
            description=entity.description,
            reference=entity.reference,
            status=entity.status.value,
        )

    def _update_model(self, model: ExpenseModel, entity: Expense) -> None:
        model.property_id = entity.property_id
        model.rental_space_id = entity.rental_space_id
        model.expense_date = entity.expense_date
        model.category = entity.category.value
        model.amount = entity.amount.amount
        model.description = entity.description
        model.reference = entity.reference
        model.status = entity.status.value

    def _to_entity(self, model: ExpenseModel) -> Expense:
        return Expense(
            id=model.id,
            property_id=model.property_id,
            rental_space_id=model.rental_space_id,
            expense_date=model.expense_date,
            category=ExpenseCategory(model.category),
            amount=Money(model.amount),
            description=model.description,
            reference=model.reference,
            status=ExpenseStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
