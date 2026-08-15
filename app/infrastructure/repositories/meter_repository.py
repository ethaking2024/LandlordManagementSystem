from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Meter
from app.domain.enums import UtilityType
from app.infrastructure.persistence.models import MeterModel
from app.infrastructure.repositories.base import RepositoryBase


class MeterRepository(RepositoryBase[Meter]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: Meter) -> Meter:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> Meter | None:
        model = self.session.get(MeterModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Meter]:
        stmt = select(MeterModel).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_rental_space(self, rental_space_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Meter]:
        stmt = (
            select(MeterModel)
            .where(MeterModel.rental_space_id == rental_space_id)
            .order_by(MeterModel.installation_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_rental_space_and_utility(
        self, rental_space_id: uuid.UUID, utility_type: UtilityType, limit: int = 100, offset: int = 0
    ) -> list[Meter]:
        stmt = (
            select(MeterModel)
            .where(
                MeterModel.rental_space_id == rental_space_id,
                MeterModel.utility_type == utility_type.value,
            )
            .order_by(MeterModel.installation_date)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_active_meters(self, rental_space_id: uuid.UUID) -> list[Meter]:
        stmt = select(MeterModel).where(
            MeterModel.rental_space_id == rental_space_id,
            MeterModel.is_active,
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_identifier(self, identifier: str) -> Meter | None:
        stmt = select(MeterModel).where(MeterModel.identifier == identifier)
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def update(self, entity: Meter) -> Meter:
        model = self.session.get(MeterModel, entity.id)
        if not model:
            raise ValueError(f"Meter with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(MeterModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: Meter) -> MeterModel:
        return MeterModel(
            id=entity.id,
            rental_space_id=entity.rental_space_id,
            utility_type=entity.utility_type.value,
            identifier=entity.identifier,
            installation_date=entity.installation_date,
            is_active=entity.is_active,
            notes=entity.notes,
        )

    def _update_model(self, model: MeterModel, entity: Meter) -> None:
        model.rental_space_id = entity.rental_space_id
        model.utility_type = entity.utility_type.value
        model.identifier = entity.identifier
        model.installation_date = entity.installation_date
        model.is_active = entity.is_active
        model.notes = entity.notes

    def _to_entity(self, model: MeterModel) -> Meter:
        return Meter(
            id=model.id,
            rental_space_id=model.rental_space_id,
            utility_type=UtilityType(model.utility_type),
            identifier=model.identifier,
            installation_date=model.installation_date,
            is_active=model.is_active,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
