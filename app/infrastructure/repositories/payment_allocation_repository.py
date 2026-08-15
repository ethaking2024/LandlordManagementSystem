from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import PaymentAllocation
from app.domain.enums import PaymentStatus
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import PaymentAllocationModel, PaymentModel
from app.infrastructure.repositories.base import RepositoryBase


class PaymentAllocationRepository(RepositoryBase[PaymentAllocation]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: PaymentAllocation) -> PaymentAllocation:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> PaymentAllocation | None:
        model = self.session.get(PaymentAllocationModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[PaymentAllocation]:
        stmt = select(PaymentAllocationModel).order_by(PaymentAllocationModel.created_at).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_payment(self, payment_id: uuid.UUID) -> list[PaymentAllocation]:
        stmt = (
            select(PaymentAllocationModel)
            .where(PaymentAllocationModel.payment_id == payment_id)
            .order_by(PaymentAllocationModel.created_at)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_bill(self, bill_id: uuid.UUID) -> list[PaymentAllocation]:
        stmt = (
            select(PaymentAllocationModel)
            .where(PaymentAllocationModel.bill_id == bill_id)
            .order_by(PaymentAllocationModel.created_at)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_valid_by_bill(self, bill_id: uuid.UUID) -> list[PaymentAllocation]:
        """Allocations against a bill whose payment is still RECORDED.

        A voided payment's allocations no longer count toward bill balances, so
        they are excluded here while their records remain intact.
        """
        stmt = (
            select(PaymentAllocationModel)
            .join(PaymentModel, PaymentModel.id == PaymentAllocationModel.payment_id)
            .where(
                PaymentAllocationModel.bill_id == bill_id,
                PaymentModel.status == PaymentStatus.RECORDED.value,
            )
            .order_by(PaymentAllocationModel.created_at)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def has_allocation_for(self, payment_id: uuid.UUID, bill_id: uuid.UUID) -> bool:
        stmt = select(PaymentAllocationModel.id).where(
            PaymentAllocationModel.payment_id == payment_id,
            PaymentAllocationModel.bill_id == bill_id,
        )
        return self.session.scalar(stmt) is not None

    def update(self, entity: PaymentAllocation) -> PaymentAllocation:
        model = self.session.get(PaymentAllocationModel, entity.id)
        if not model:
            raise ValueError(f"PaymentAllocation with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(PaymentAllocationModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: PaymentAllocation) -> PaymentAllocationModel:
        return PaymentAllocationModel(
            id=entity.id,
            payment_id=entity.payment_id,
            bill_id=entity.bill_id,
            allocated_amount=entity.allocated_amount.amount,
        )

    def _update_model(self, model: PaymentAllocationModel, entity: PaymentAllocation) -> None:
        model.payment_id = entity.payment_id
        model.bill_id = entity.bill_id
        model.allocated_amount = entity.allocated_amount.amount

    def _to_entity(self, model: PaymentAllocationModel) -> PaymentAllocation:
        return PaymentAllocation(
            id=model.id,
            payment_id=model.payment_id,
            bill_id=model.bill_id,
            allocated_amount=Money(model.allocated_amount),
            created_at=model.created_at,
        )
