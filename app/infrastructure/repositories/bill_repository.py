from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Bill, BillLine
from app.domain.enums import BillCategory, BillStatus
from app.domain.value_objects import BillingPeriod, Money
from app.infrastructure.persistence.models import BillLineModel, BillModel
from app.infrastructure.repositories.base import RepositoryBase


class BillRepository(RepositoryBase[Bill]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: Bill) -> Bill:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> Bill | None:
        model = self.session.get(BillModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Bill]:
        stmt = select(BillModel).order_by(BillModel.period_start).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_agreement(self, agreement_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Bill]:
        stmt = (
            select(BillModel)
            .where(BillModel.agreement_id == agreement_id)
            .order_by(BillModel.period_start)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_agreement_and_period(
        self, agreement_id: uuid.UUID, period_start: date, period_end: date
    ) -> Bill | None:
        stmt = select(BillModel).where(
            BillModel.agreement_id == agreement_id,
            BillModel.period_start == period_start,
            BillModel.period_end == period_end,
        )
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def has_bill_for_period(self, agreement_id: uuid.UUID, period_start: date, period_end: date) -> bool:
        stmt = select(BillModel.id).where(
            BillModel.agreement_id == agreement_id,
            BillModel.period_start == period_start,
            BillModel.period_end == period_end,
        )
        return self.session.scalar(stmt) is not None

    def get_by_status(self, status: BillStatus, limit: int = 100, offset: int = 0) -> list[Bill]:
        stmt = (
            select(BillModel)
            .where(BillModel.status == status.value)
            .order_by(BillModel.period_start)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def update(self, entity: Bill) -> Bill:
        model = self.session.get(BillModel, entity.id)
        if not model:
            raise ValueError(f"Bill with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(BillModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: Bill) -> BillModel:
        model = BillModel(
            id=entity.id,
            agreement_id=entity.agreement_id,
            tenant_id=entity.tenant_id,
            rental_space_id=entity.rental_space_id,
            period_start=entity.period.start,
            period_end=entity.period.end,
            billing_date=entity.billing_date,
            status=entity.status.value,
            total_amount=entity.total.amount,
            notes=entity.notes,
        )
        for line in entity.lines:
            model.lines.append(self._line_to_model(line, entity.id))
        return model

    def _update_model(self, model: BillModel, entity: Bill) -> None:
        model.agreement_id = entity.agreement_id
        model.tenant_id = entity.tenant_id
        model.rental_space_id = entity.rental_space_id
        model.period_start = entity.period.start
        model.period_end = entity.period.end
        model.billing_date = entity.billing_date
        model.status = entity.status.value
        model.total_amount = entity.total.amount
        model.notes = entity.notes
        model.lines.clear()
        for line in entity.lines:
            model.lines.append(self._line_to_model(line, entity.id))

    def _line_to_model(self, line: BillLine, bill_id: uuid.UUID) -> BillLineModel:
        return BillLineModel(
            id=line.id,
            bill_id=bill_id,
            category=line.category.value,
            description=line.description,
            quantity=line.quantity,
            unit_rate=line.unit_rate.amount if line.unit_rate else None,
            amount=line.amount.amount,
            config_type=line.config_type,
            meter_id=line.meter_id,
            meter_identifier=line.meter_identifier,
            previous_reading=line.previous_reading,
            current_reading=line.current_reading,
            consumption=line.consumption,
            tariff_rate=line.tariff_rate.amount if line.tariff_rate else None,
            tariff_effective_from=line.tariff_effective_from,
        )

    def _to_entity(self, model: BillModel) -> Bill:
        lines = [self._to_line_entity(line_model) for line_model in model.lines]
        return Bill(
            id=model.id,
            agreement_id=model.agreement_id,
            tenant_id=model.tenant_id,
            rental_space_id=model.rental_space_id,
            period=BillingPeriod(model.period_start, model.period_end),
            billing_date=model.billing_date,
            status=BillStatus(model.status),
            notes=model.notes,
            lines=lines,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_line_entity(self, model: BillLineModel) -> BillLine:
        return BillLine(
            id=model.id,
            bill_id=model.bill_id,
            category=BillCategory(model.category),
            description=model.description,
            quantity=model.quantity,
            unit_rate=Money(model.unit_rate) if model.unit_rate is not None else None,
            amount=Money(model.amount),
            config_type=model.config_type,
            meter_id=model.meter_id,
            meter_identifier=model.meter_identifier,
            previous_reading=model.previous_reading,
            current_reading=model.current_reading,
            consumption=model.consumption,
            tariff_rate=Money(model.tariff_rate) if model.tariff_rate is not None else None,
            tariff_effective_from=model.tariff_effective_from,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
