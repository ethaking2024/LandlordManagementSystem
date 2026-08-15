from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Deposit
from app.domain.enums import DepositStatus
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import DepositModel
from app.infrastructure.repositories.base import RepositoryBase


class DepositRepository(RepositoryBase[Deposit]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: Deposit) -> Deposit:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> Deposit | None:
        model = self.session.get(DepositModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Deposit]:
        stmt = select(DepositModel).order_by(DepositModel.received_date).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_agreement(self, agreement_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Deposit]:
        stmt = (
            select(DepositModel)
            .where(DepositModel.agreement_id == agreement_id)
            .order_by(DepositModel.received_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Deposit]:
        stmt = (
            select(DepositModel)
            .where(DepositModel.tenant_id == tenant_id)
            .order_by(DepositModel.received_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_status(self, status: DepositStatus, limit: int = 100, offset: int = 0) -> list[Deposit]:
        stmt = (
            select(DepositModel)
            .where(DepositModel.status == status.value)
            .order_by(DepositModel.received_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_held_by_agreement(self, agreement_id: uuid.UUID) -> list[Deposit]:
        stmt = select(DepositModel).where(
            DepositModel.agreement_id == agreement_id,
            DepositModel.status == DepositStatus.HELD.value,
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def update(self, entity: Deposit) -> Deposit:
        model = self.session.get(DepositModel, entity.id)
        if not model:
            raise ValueError(f"Deposit with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(DepositModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: Deposit) -> DepositModel:
        return DepositModel(
            id=entity.id,
            agreement_id=entity.agreement_id,
            tenant_id=entity.tenant_id,
            amount=entity.amount.amount,
            received_date=entity.received_date,
            status=entity.status.value,
            reference=entity.reference,
            notes=entity.notes,
        )

    def _update_model(self, model: DepositModel, entity: Deposit) -> None:
        model.agreement_id = entity.agreement_id
        model.tenant_id = entity.tenant_id
        model.amount = entity.amount.amount
        model.received_date = entity.received_date
        model.status = entity.status.value
        model.reference = entity.reference
        model.notes = entity.notes

    def _to_entity(self, model: DepositModel) -> Deposit:
        return Deposit(
            id=model.id,
            agreement_id=model.agreement_id,
            tenant_id=model.tenant_id,
            amount=Money(model.amount),
            received_date=model.received_date,
            status=DepositStatus(model.status),
            reference=model.reference,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
