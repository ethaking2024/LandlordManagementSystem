from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Owner
from app.domain.value_objects import PhoneNumber
from app.infrastructure.persistence.models import OwnerModel
from app.infrastructure.repositories.base import RepositoryBase


class OwnerRepository(RepositoryBase[Owner]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: Owner) -> Owner:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> Owner | None:
        model = self.session.get(OwnerModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Owner]:
        stmt = select(OwnerModel).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_name(self, name: str) -> Owner | None:
        stmt = select(OwnerModel).where(OwnerModel.name == name)
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def update(self, entity: Owner) -> Owner:
        model = self.session.get(OwnerModel, entity.id)
        if not model:
            raise ValueError(f"Owner with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(OwnerModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: Owner) -> OwnerModel:
        return OwnerModel(
            id=entity.id,
            name=entity.name,
            phone=entity.phone.number if entity.phone else None,
            email=entity.email,
            address=entity.address,
            notes=entity.notes,
        )

    def _update_model(self, model: OwnerModel, entity: Owner) -> None:
        model.name = entity.name
        model.phone = entity.phone.number if entity.phone else None
        model.email = entity.email
        model.address = entity.address
        model.notes = entity.notes

    def _to_entity(self, model: OwnerModel) -> Owner:
        return Owner(
            id=model.id,
            name=model.name,
            phone=PhoneNumber(model.phone) if model.phone else None,
            email=model.email,
            address=model.address,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
