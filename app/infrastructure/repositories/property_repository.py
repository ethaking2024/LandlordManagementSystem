from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Property
from app.infrastructure.persistence.models import PropertyModel
from app.infrastructure.repositories.base import RepositoryBase


class PropertyRepository(RepositoryBase[Property]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: Property) -> Property:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> Property | None:
        model = self.session.get(PropertyModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Property]:
        stmt = select(PropertyModel).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_owner(self, owner_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Property]:
        stmt = select(PropertyModel).where(PropertyModel.owner_id == owner_id).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def update(self, entity: Property) -> Property:
        model = self.session.get(PropertyModel, entity.id)
        if not model:
            raise ValueError(f"Property with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(PropertyModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: Property) -> PropertyModel:
        return PropertyModel(
            id=entity.id,
            owner_id=entity.owner_id,
            name=entity.name,
            address=entity.address,
            notes=entity.notes,
        )

    def _update_model(self, model: PropertyModel, entity: Property) -> None:
        model.name = entity.name
        model.address = entity.address
        model.notes = entity.notes

    def _to_entity(self, model: PropertyModel) -> Property:
        return Property(
            id=model.id,
            owner_id=model.owner_id,
            name=model.name,
            address=model.address,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
