from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import RentalSpace
from app.domain.enums import SpaceType
from app.infrastructure.persistence.models import RentalSpaceModel
from app.infrastructure.repositories.base import RepositoryBase


class RentalSpaceRepository(RepositoryBase[RentalSpace]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: RentalSpace) -> RentalSpace:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> RentalSpace | None:
        model = self.session.get(RentalSpaceModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[RentalSpace]:
        stmt = select(RentalSpaceModel).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_property(self, property_id: uuid.UUID, active_only: bool = True, limit: int = 100, offset: int = 0) -> list[RentalSpace]:
        stmt = select(RentalSpaceModel).where(RentalSpaceModel.property_id == property_id)
        if active_only:
            stmt = stmt.where(RentalSpaceModel.is_active)
        stmt = stmt.offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_active_spaces(self, property_id: uuid.UUID) -> list[RentalSpace]:
        stmt = select(RentalSpaceModel).where(
            RentalSpaceModel.property_id == property_id,
            RentalSpaceModel.is_active,
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def update(self, entity: RentalSpace) -> RentalSpace:
        model = self.session.get(RentalSpaceModel, entity.id)
        if not model:
            raise ValueError(f"RentalSpace with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(RentalSpaceModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: RentalSpace) -> RentalSpaceModel:
        return RentalSpaceModel(
            id=entity.id,
            property_id=entity.property_id,
            name=entity.name,
            space_type=entity.space_type.value,
            floor_label=entity.floor_label,
            description=entity.description,
            is_active=entity.is_active,
        )

    def _update_model(self, model: RentalSpaceModel, entity: RentalSpace) -> None:
        model.name = entity.name
        model.space_type = entity.space_type.value
        model.floor_label = entity.floor_label
        model.description = entity.description
        model.is_active = entity.is_active

    def _to_entity(self, model: RentalSpaceModel) -> RentalSpace:
        return RentalSpace(
            id=model.id,
            property_id=model.property_id,
            name=model.name,
            space_type=SpaceType(model.space_type),
            floor_label=model.floor_label,
            description=model.description,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
