from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Payment
from app.domain.enums import PaymentMethod, PaymentStatus
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import PaymentModel
from app.infrastructure.repositories.base import RepositoryBase


class PaymentRepository(RepositoryBase[Payment]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: Payment) -> Payment:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> Payment | None:
        model = self.session.get(PaymentModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Payment]:
        stmt = select(PaymentModel).order_by(PaymentModel.payment_date).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Payment]:
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.tenant_id == tenant_id)
            .order_by(PaymentModel.payment_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_date_range(self, start: date, end: date, limit: int = 10000, offset: int = 0) -> list[Payment]:
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.payment_date >= start, PaymentModel.payment_date <= end)
            .order_by(PaymentModel.payment_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_status(self, status: PaymentStatus, limit: int = 100, offset: int = 0) -> list[Payment]:
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.status == status.value)
            .order_by(PaymentModel.payment_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def update(self, entity: Payment) -> Payment:
        model = self.session.get(PaymentModel, entity.id)
        if not model:
            raise ValueError(f"Payment with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(PaymentModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: Payment) -> PaymentModel:
        return PaymentModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            payment_date=entity.payment_date,
            amount=entity.amount.amount,
            payment_method=entity.payment_method.value,
            reference=entity.reference,
            notes=entity.notes,
            status=entity.status.value,
        )

    def _update_model(self, model: PaymentModel, entity: Payment) -> None:
        model.tenant_id = entity.tenant_id
        model.payment_date = entity.payment_date
        model.amount = entity.amount.amount
        model.payment_method = entity.payment_method.value
        model.reference = entity.reference
        model.notes = entity.notes
        model.status = entity.status.value

    def _to_entity(self, model: PaymentModel) -> Payment:
        return Payment(
            id=model.id,
            tenant_id=model.tenant_id,
            payment_date=model.payment_date,
            amount=Money(model.amount),
            payment_method=PaymentMethod(model.payment_method),
            reference=model.reference,
            notes=model.notes,
            status=PaymentStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
