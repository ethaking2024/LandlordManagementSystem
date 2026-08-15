from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import MeterReading
from app.domain.value_objects import MeterReadingValue
from app.infrastructure.persistence.models import MeterReadingModel
from app.infrastructure.repositories.base import RepositoryBase


class MeterReadingRepository(RepositoryBase[MeterReading]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: MeterReading) -> MeterReading:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> MeterReading | None:
        model = self.session.get(MeterReadingModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[MeterReading]:
        stmt = select(MeterReadingModel).order_by(MeterReadingModel.reading_date).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_meter(self, meter_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[MeterReading]:
        stmt = (
            select(MeterReadingModel)
            .where(MeterReadingModel.meter_id == meter_id)
            .order_by(MeterReadingModel.reading_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_meter_between(
        self, meter_id: uuid.UUID, start_date: date | None = None, end_date: date | None = None
    ) -> list[MeterReading]:
        stmt = select(MeterReadingModel).where(MeterReadingModel.meter_id == meter_id)
        if start_date:
            stmt = stmt.where(MeterReadingModel.reading_date >= start_date)
        if end_date:
            stmt = stmt.where(MeterReadingModel.reading_date <= end_date)
        stmt = stmt.order_by(MeterReadingModel.reading_date)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_latest_reading(self, meter_id: uuid.UUID) -> MeterReading | None:
        stmt = (
            select(MeterReadingModel)
            .where(MeterReadingModel.meter_id == meter_id)
            .order_by(MeterReadingModel.reading_date.desc())
            .limit(1)
        )
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def get_reading_on_date(self, meter_id: uuid.UUID, reading_date: date) -> MeterReading | None:
        stmt = select(MeterReadingModel).where(
            MeterReadingModel.meter_id == meter_id,
            MeterReadingModel.reading_date == reading_date,
        )
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def has_reading_on_date(self, meter_id: uuid.UUID, reading_date: date) -> bool:
        stmt = select(MeterReadingModel.id).where(
            MeterReadingModel.meter_id == meter_id,
            MeterReadingModel.reading_date == reading_date,
        )
        return self.session.scalar(stmt) is not None

    def update(self, entity: MeterReading) -> MeterReading:
        model = self.session.get(MeterReadingModel, entity.id)
        if not model:
            raise ValueError(f"MeterReading with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(MeterReadingModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: MeterReading) -> MeterReadingModel:
        return MeterReadingModel(
            id=entity.id,
            meter_id=entity.meter_id,
            reading_date=entity.reading_date,
            value=entity.value.value,
            notes=entity.notes,
        )

    def _update_model(self, model: MeterReadingModel, entity: MeterReading) -> None:
        model.meter_id = entity.meter_id
        model.reading_date = entity.reading_date
        model.value = entity.value.value
        model.notes = entity.notes

    def _to_entity(self, model: MeterReadingModel) -> MeterReading:
        return MeterReading(
            id=model.id,
            meter_id=model.meter_id,
            reading_date=model.reading_date,
            value=MeterReadingValue(model.value),
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
