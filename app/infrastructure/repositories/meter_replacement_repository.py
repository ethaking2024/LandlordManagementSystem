from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import MeterReplacement
from app.infrastructure.persistence.models import MeterReplacementModel
from app.infrastructure.repositories.base import RepositoryBase


class MeterReplacementRepository(RepositoryBase[MeterReplacement]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: MeterReplacement) -> MeterReplacement:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> MeterReplacement | None:
        model = self.session.get(MeterReplacementModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[MeterReplacement]:
        stmt = select(MeterReplacementModel).order_by(MeterReplacementModel.replaced_on).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_old_meter(self, old_meter_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[MeterReplacement]:
        stmt = (
            select(MeterReplacementModel)
            .where(MeterReplacementModel.old_meter_id == old_meter_id)
            .order_by(MeterReplacementModel.replaced_on)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_new_meter(self, new_meter_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[MeterReplacement]:
        stmt = (
            select(MeterReplacementModel)
            .where(MeterReplacementModel.new_meter_id == new_meter_id)
            .order_by(MeterReplacementModel.replaced_on)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def update(self, entity: MeterReplacement) -> MeterReplacement:
        model = self.session.get(MeterReplacementModel, entity.id)
        if not model:
            raise ValueError(f"MeterReplacement with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(MeterReplacementModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: MeterReplacement) -> MeterReplacementModel:
        return MeterReplacementModel(
            id=entity.id,
            old_meter_id=entity.old_meter_id,
            new_meter_id=entity.new_meter_id,
            replaced_on=entity.replaced_on,
            notes=entity.notes,
        )

    def _update_model(self, model: MeterReplacementModel, entity: MeterReplacement) -> None:
        model.old_meter_id = entity.old_meter_id
        model.new_meter_id = entity.new_meter_id
        model.replaced_on = entity.replaced_on
        model.notes = entity.notes

    def _to_entity(self, model: MeterReplacementModel) -> MeterReplacement:
        return MeterReplacement(
            id=model.id,
            old_meter_id=model.old_meter_id,
            new_meter_id=model.new_meter_id,
            replaced_on=model.replaced_on,
            notes=model.notes,
            created_at=model.created_at,
        )
