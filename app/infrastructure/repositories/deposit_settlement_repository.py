from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import DepositDeduction, DepositSettlement
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import DepositDeductionModel, DepositSettlementModel
from app.infrastructure.repositories.base import RepositoryBase


class DepositSettlementRepository(RepositoryBase[DepositSettlement]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: DepositSettlement) -> DepositSettlement:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> DepositSettlement | None:
        model = self.session.get(DepositSettlementModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[DepositSettlement]:
        stmt = select(DepositSettlementModel).order_by(DepositSettlementModel.settlement_date).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_deposit(self, deposit_id: uuid.UUID) -> DepositSettlement | None:
        stmt = select(DepositSettlementModel).where(DepositSettlementModel.deposit_id == deposit_id)
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def has_settlement_for_deposit(self, deposit_id: uuid.UUID) -> bool:
        stmt = select(DepositSettlementModel.id).where(DepositSettlementModel.deposit_id == deposit_id)
        return self.session.scalar(stmt) is not None

    def update(self, entity: DepositSettlement) -> DepositSettlement:
        model = self.session.get(DepositSettlementModel, entity.id)
        if not model:
            raise ValueError(f"Deposit settlement with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(DepositSettlementModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: DepositSettlement) -> DepositSettlementModel:
        model = DepositSettlementModel(
            id=entity.id,
            deposit_id=entity.deposit_id,
            settlement_date=entity.settlement_date,
            refund_amount=entity.refund_amount.amount if entity.refund_amount else None,
            notes=entity.notes,
        )
        for deduction in entity.deductions:
            model.deductions.append(self._deduction_to_model(deduction))
        return model

    def _update_model(self, model: DepositSettlementModel, entity: DepositSettlement) -> None:
        model.deposit_id = entity.deposit_id
        model.settlement_date = entity.settlement_date
        model.refund_amount = entity.refund_amount.amount if entity.refund_amount else None
        model.notes = entity.notes

    def _deduction_to_model(self, deduction: DepositDeduction) -> DepositDeductionModel:
        return DepositDeductionModel(
            id=deduction.id,
            settlement_id=deduction.settlement_id,
            amount=deduction.amount.amount,
            reason=deduction.reason,
        )

    def _to_entity(self, model: DepositSettlementModel) -> DepositSettlement:
        deductions = [self._to_deduction_entity(d) for d in model.deductions]
        return DepositSettlement(
            id=model.id,
            deposit_id=model.deposit_id,
            settlement_date=model.settlement_date,
            refund_amount=Money(model.refund_amount) if model.refund_amount is not None else None,
            notes=model.notes,
            deductions=deductions,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_deduction_entity(self, model: DepositDeductionModel) -> DepositDeduction:
        return DepositDeduction(
            id=model.id,
            settlement_id=model.settlement_id,
            amount=Money(model.amount),
            reason=model.reason,
            created_at=model.created_at,
        )
